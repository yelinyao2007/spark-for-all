import re
from fractions import Fraction
from .models import SessionState, TopicState, Strategy, Understanding
from .safety import normalize, safety_reply
from .search import ServiceError

WARNINGS = {
    'search_quota':'资料搜索额度暂时用完了，请稍后再试。',
    'search_auth':'资料搜索暂时无法连接，请管理员检查配置。',
    'search_unavailable':'资料搜索暂时不可用，这次没有可核对的来源。',
    'search_response':'资料搜索返回异常，这次没有可核对的来源。',
    'unsafe_query':'这个问题需要先去掉个人信息。',
    'llm_not_configured':'学习模型尚未连接，暂时不能生成讲解。',
    'llm_unavailable':'学习模型暂时没有回应，请稍后再试。',
}
CYCLE = [Strategy.SIMPLE, Strategy.ANALOGY, Strategy.STEPS, Strategy.GUIDED, Strategy.EXAMPLE]

def public_state(state):
    result = state.model_dump(mode='json')
    for t in result['topics'].values():
        t.pop('question',None)
        t.pop('sources',None)
        t.pop('checked_questions',None)
        t.pop('previous_explanation',None)
        quiz = t.pop('pending_quiz',None)
        if quiz:
            t['quiz'] = {k:v for k,v in quiz.items() if k not in ('answer','explanation')}
        else:
            t['quiz'] = None
    return result

def equivalent(answer, expected):
    a,b = normalize(answer).replace(' ',''),normalize(expected).replace(' ','')
    if a == b:
        return True
    if re.fullmatch(r'-?\d+(?:/\d+|\.\d+)?',a) and re.fullmatch(r'-?\d+(?:/\d+|\.\d+)?',b):
        try:
            return Fraction(a) == Fraction(b)
        except (ValueError,ZeroDivisionError):
            pass
    return False

class Agent:
    def __init__(self, generator, search, store, mode):
        self.generator, self.search, self.store, self.mode = generator, search, store, mode
    def result(self, state, explanation, sources=None, warnings=None, visual='none'):
        return {'explanation':explanation,'state':public_state(state),'sources':[s.model_dump(mode='json') for s in (sources or [])],
                'warnings':warnings or [], 'visual':visual,'mode':self.mode,'generated':True}
    async def turn(self, state: SessionState, turn):
        text = normalize(turn.text)
        blocked = safety_reply(text)
        if blocked:
            return self.result(state, blocked)
        action = turn.action
        if action == 'ask':
            if re.search(r'没听懂|不明白|不理解|不懂|太难|听不懂',text): action = 'again'
            elif re.search(r'换.{0,3}例子|举.{0,3}例子',text): action = 'example'
            elif text in ('我懂了','明白了'): action = 'understood'
            elif text in ('考考我','练习一下'): action = 'quiz'
        topic = state.topics.get(state.current_topic)
        if action == 'skip':
            if topic: topic.pending_quiz = None
            state.current_topic = None
            return self.result(state, '好呀，我们可以休息一下，或者换一个想探索的问题。')
        if action != 'ask' and topic is None:
            return self.result(state, '先告诉我一个想学习的数学或科学问题吧。')
        if action == 'understood':
            if not topic.self_reported:
                self.store.increment(self.mode,'self_reported_improvements')
            topic.self_reported = True
            if topic.understanding != Understanding.UNDERSTOOD:
                topic.understanding = Understanding.PARTIAL
            return self.result(state, '很高兴你觉得更清楚了！这只是你的自我感受，还不代表完全掌握。可以用自己的话讲一讲，或做一道练习。')
        if action == 'answer':
            quiz = topic.pending_quiz
            if not quiz:
                return self.result(state,'这道题已经完成了。点击“考考我”可以试一道新题。')
            if not text:
                return self.result(state,'先选择一个答案，或者写下你的想法吧。')
            correct = equivalent(text, quiz.answer)
            topic.completed_quizzes += 1
            topic.pending_quiz = None
            is_new = quiz.question not in topic.checked_questions
            topic.correct_checks += int(correct and is_new)
            if is_new: topic.checked_questions.append(quiz.question)
            topic.understanding = Understanding.UNDERSTOOD if correct and topic.correct_checks >= 2 else (Understanding.PARTIAL if correct else Understanding.REINFORCE)
            state.interactions += 1
            self.store.increment(self.mode,'interactions')
            self.store.increment(self.mode,'quizzes')
            feedback = '这次答对了！' if correct else '谢谢你认真尝试。我们再看一下：'
            if quiz.kind == 'short_answer' and not correct:
                feedback += '自动检查暂时只支持标准答案或等值数字；表达不同也可能有道理，可以请老师一起看看。'
            return self.result(state,feedback + quiz.explanation + '一次回答不能说明已经掌握，我们慢慢来。')
        sources, warnings = list(topic.sources) if topic else [], []
        if action == 'ask':
            if not text:
                return self.result(state,'写下你想探索的问题吧。')
            try:
                intent = await self.generator.analyze(text,state)
            except ServiceError as exc:
                return self.result(state,WARNINGS[exc.code],warnings=[exc.code])
            if safety_reply(intent.topic) or safety_reply(intent.search_query):
                return self.result(state,'请只发送数学或科学问题，不要加入个人信息。')
            if intent.intent in ('confusion','example','practice','understood','answer') and topic:
                mapped = {'confusion':'again','example':'example','practice':'quiz','understood':'understood','answer':'answer'}
                return await self.turn(state,turn.model_copy(update={'action':mapped[intent.intent]}))
            if intent.topic not in state.topics:
                if len(state.topics) >= 30:
                    return self.result(state,'这次已探索了很多话题。可以结束本次学习，再开始一次新的学习。')
                state.topics[intent.topic] = TopicState(topic=intent.topic,question=text)
                self.store.increment(self.mode,'topics_explored')
            state.current_topic = intent.topic
            topic = state.topics[intent.topic]
            sources = []
            topic.sources = []
            topic.question = text
            topic.strategy = Strategy.SIMPLE
            topic.confusion_count = 0
            if intent.retrieval:
                try:
                    sources = await self.search.search(intent.search_query or intent.topic)
                    topic.sources = sources
                    if not sources: warnings.append('no_sources')
                except ServiceError as exc:
                    warnings.append(exc.code)
        elif action in ('again','example'):
            topic.confusion_count += 1
            topic.understanding = Understanding.REINFORCE
            if topic.confusion_count > 5:
                topic.pending_quiz = None
                return self.result(state,'已经试了几种方法，没关系。可以先休息、换个问题，或请身边老师和你一起看看卡在哪一步。')
            current = CYCLE.index(topic.strategy) if topic.strategy in CYCLE else 0
            topic.strategy = CYCLE[(current+1)%len(CYCLE)] if action=='again' else (Strategy.EXAMPLE if topic.strategy != Strategy.EXAMPLE else Strategy.ANALOGY)
        elif action == 'quiz':
            topic.strategy = Strategy.QUIZ
        topic.pending_quiz = None
        topic.attempts += 1
        try:
            lesson = await self.generator.lesson(state,topic,text,sources)
            blocked = safety_reply(lesson.explanation)
            if blocked or re.search(r'https?://|www\.',lesson.explanation):
                raise ServiceError('llm_unavailable')
            if topic.previous_explanation == lesson.explanation:
                raise ServiceError('llm_unavailable')
            if lesson.quiz and safety_reply(' '.join([lesson.quiz.question,lesson.quiz.answer,lesson.quiz.explanation,*lesson.quiz.options])):
                raise ServiceError('llm_unavailable')
        except ServiceError as exc:
            return self.result(state,WARNINGS[exc.code],sources,warnings+[exc.code])
        if action in ('again','example'):
            self.store.increment(self.mode,'alternative_explanations')
        topic.previous_explanation = lesson.explanation
        topic.pending_quiz = lesson.quiz
        if topic.understanding == Understanding.UNKNOWN:
            topic.understanding = Understanding.EXPLORING
        state.interactions += 1
        self.store.increment(self.mode,'interactions')
        # Only existing retrieval IDs can be attributed. Unknown IDs never become links.
        cited = [s for s in sources if s.id in lesson.source_ids]
        if sources and not cited:
            warnings.append('sources_not_cited')
        return self.result(state,lesson.explanation,sources,warnings,lesson.visual)
