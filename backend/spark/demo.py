"""Explicit offline demonstration engine; never used silently in live mode."""
import re
from fractions import Fraction
from .llm import Intent
from .models import Lesson, Quiz, Strategy

class DemoGenerator:
    async def analyze(self, text, state):
        topic = '等值分数' if re.search(r'\d+\s*/\s*\d+|分数|披萨', text) else ('月相变化' if '月' in text else text[:40])
        if state.current_topic and any(w in text for w in ['为什么呢','然后呢','这个']):
            topic = state.current_topic
        return Intent(topic=topic, intent='question', retrieval=topic != '等值分数', search_query=topic+' 科学解释')
    async def lesson(self, state, topic, text, sources):
        fractions = re.findall(r'(\d+)\s*/\s*(\d+)', topic.question)
        if topic.topic != '等值分数' or len(fractions) < 2:
            return Lesson(explanation='现在是离线演示模式，通用讲解需要连接语言模型。可以输入任意两组分数，例如“为什么 1/2 和 2/4 一样大？”，体验不同教学方法。检索到的资料可在来源区阅读。')
        try:
            a,b = [Fraction(int(n),int(d)) for n,d in fractions[:2]]
        except (ValueError, ZeroDivisionError):
            return Lesson(explanation='分母表示平均分成的份数，不能是零。试着换成一个大于零的分母吧。')
        n,d = map(int, fractions[0]); m,e = map(int, fractions[1])
        same = a == b
        relation = '一样大' if same else '不一样大'
        introduction = f'{n}/{d} 和 {m}/{e} {relation}。'
        methods = {
            Strategy.SIMPLE: f'分母告诉我们整体平均分成几份，分子告诉我们取了几份。化成最简分数，它们分别是 {a} 和 {b}，比较这两个数就能看出关系。',
            Strategy.ANALOGY: f'想象两张同样大的披萨。第一张平均切成 {d} 份，拿 {n} 份；第二张切成 {e} 份，拿 {m} 份。小块数量不同，要比较拿到的总面积，而不只数块数。',
            Strategy.STEPS: f'先写出 {n} ÷ {d}，再写出 {m} ÷ {e}。交叉相乘也能比较：{n} × {e} = {n*e}，{m} × {d} = {m*d}。乘积相等时，两个分数相等。',
            Strategy.GUIDED: f'想一想：把一块再平均切成两小块，总量会改变吗？把 {n}/{d} 的每份再切两份，取到的份数和总份数都翻倍，变成 {n*2}/{d*2}，总量没有改变。',
            Strategy.EXAMPLE: f'拿一条纸带平均分成 {d} 格，涂上 {n} 格。现在每格再分成两格，涂色部分仍是原来那么多，只是可以数成 {n*2}/{d*2}。',
            Strategy.QUIZ: '分子和分母同时乘同一个非零数，表示的量不变。我们用一道新题试试。'}
        k = topic.attempts + 1
        answer = f'{n*k}/{d*k}'
        options = [answer, f'{n*k+1}/{d*k}', f'{n}/{d*k+1}']
        if topic.attempts % 3 == 0:
            quiz = Quiz(kind='short_answer',question=f'{n}/{d} 的分子分母同时乘 {k}，会得到哪个分数？',answer=answer,explanation='分子分母同时乘相同的非零数，总量不变。')
        elif topic.attempts % 3 == 2:
            quiz = Quiz(kind='true_false',question=f'{n}/{d} 与 {answer} 表示的量相同，对吗？',options=['对','不对'],answer='对',explanation='我们把每一份继续等分，总量没有改变。')
        else:
            quiz = Quiz(kind='multiple_choice',question=f'哪个分数和 {n}/{d} 一样大？',options=options,answer=answer,explanation=f'分子和分母同时乘 {k}，所以 {n}/{d} = {answer}。')
        return Lesson(explanation=introduction+methods[topic.strategy]+('慢慢看，每次只比较一个整体就好。' if state.grade == 4 else ''),quiz=quiz,visual='fractions' if a==b==Fraction(1,2) else 'none')
