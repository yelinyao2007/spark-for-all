<script setup lang="ts">
import { computed,ref,onMounted,onBeforeUnmount,nextTick } from 'vue'
import { api,type State,type Reply,type Source } from './services/api'
import TeacherAvatar from './components/TeacherAvatar.vue'
import FractionVisual from './components/FractionVisual.vue'
const page=ref<'home'|'learn'|'summary'|'impact'>('home'),grade=ref(5),state=ref<State|null>(null)
const health=ref<{mode:string;llm_configured:boolean}|null>(null),busy=ref(false),error=ref(''),text=ref(''),textOnly=ref(false),speech=ref(''),answer=ref('')
const teacher=ref<InstanceType<typeof TeacherAvatar>|null>(null),conversation=ref<HTMLElement|null>(null)
const messages=ref<{role:string;text:string;sources:Source[];visual:string;warnings:string[]}[]>([])
const impact=ref<{live:Record<string,number>;demo:Record<string,number>;note:string}|null>(null)
const current=computed(()=>state.value?.current_topic?state.value.topics[state.value.current_topic]:null)
const topics=computed(()=>Object.values(state.value?.topics??{}))
const states:Record<string,string>={unknown:'刚刚开始',exploring:'正在探索',partially_understood:'开始理解',understood:'多次练习有进步',needs_reinforcement:'再巩固一下'}
const strategies:Record<string,string>={simple:'简单讲解',analogy:'生活类比',steps:'一步一步',guided:'一起想一想',example:'动手小例子',quiz:'小小练习'}
const warningLabels:Record<string,string>={search_quota:'搜索额度暂时用完',search_auth:'搜索配置暂时不可用',search_unavailable:'搜索暂时不可用，本次没有已检索来源',search_response:'来源暂时无法读取',no_sources:'没有找到适合的来源',sources_not_cited:'以下是检索资料，尚未确认它们支持本次讲解',llm_not_configured:'学习模型尚未连接',llm_unavailable:'学习模型暂时不可用',unsafe_query:'请去掉个人信息'}
async function start(question=''){
 busy.value=true;error.value=''
 try{if(!state.value)state.value=await api<State>('/session','POST',{grade:grade.value});page.value='learn';if(question){text.value=question}}
 catch(e){error.value=(e as Error).message}finally{busy.value=false}
 if(question&&state.value)await send('ask')
}
function questionKey(event:KeyboardEvent){if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();void send('ask')}}
async function send(action='ask',value?:string){
 if(busy.value)return
 const content=value??text.value
 if(action==='ask'&&!content.trim())return
 teacher.value?.interrupt();busy.value=true;error.value=''
 const display:Record<string,string>={again:'我还是没听懂。',example:'换个例子吧。',understood:'我懂了！',quiz:'考考我',skip:'换个话题'}
 try{
  const reply=await api<Reply>('/turn','POST',{action,text:action==='ask'||action==='answer'?content:''})
  messages.value.push({role:'student',text:display[action]??content,sources:[],visual:'none',warnings:[]})
  messages.value.push({role:'teacher',text:reply.explanation,sources:reply.sources,visual:reply.visual,warnings:reply.warnings})
  state.value=reply.state;text.value='';answer.value='';speech.value=reply.explanation
  await nextTick();conversation.value?.scrollTo({top:conversation.value.scrollHeight,behavior:'smooth'})
 }catch(e){error.value=(e as Error).message}finally{busy.value=false}
}
async function showImpact(){try{impact.value=await api('/impact');page.value='impact'}catch(e){error.value=(e as Error).message}}
async function end(){try{await api('/session','DELETE');state.value=null;messages.value=[];speech.value='';page.value='home'}catch(e){error.value=(e as Error).message}}
// Browser speech recognition is optional and activated only by a user gesture.
interface Recognition {lang:string;continuous:boolean;interimResults:boolean;onresult:((e:{results:{[key:number]:{[key:number]:{transcript:string}}}})=>void)|null;onerror:(()=>void)|null;onend:(()=>void)|null;start():void;stop():void;abort():void}
const SpeechRecognition=(window as unknown as {SpeechRecognition?:new()=>Recognition;webkitSpeechRecognition?:new()=>Recognition}).SpeechRecognition??(window as unknown as {webkitSpeechRecognition?:new()=>Recognition}).webkitSpeechRecognition
const listening=ref(false);let recognition:Recognition|undefined
function voice(){
 if(listening.value){recognition?.stop();return}
 if(!SpeechRecognition)return
 recognition=new SpeechRecognition();recognition.lang='zh-CN';recognition.continuous=false;recognition.interimResults=false
 recognition.onresult=e=>{text.value=e.results[0][0].transcript}
 recognition.onerror=()=>{error.value='麦克风未获授权或语音服务不可用，可以继续打字。';listening.value=false}
 recognition.onend=()=>{listening.value=false}
 try{recognition.start();listening.value=true}catch{error.value='语音暂时不可用，请打字。'}
}
onMounted(async()=>{try{health.value=await api('/health')}catch{error.value='暂时连接不上学习服务，请稍后刷新。'}})
onBeforeUnmount(()=>recognition?.abort())
</script>
<template>
 <header class="site-header"><a class="brand" href="#" @click.prevent="page='home'"><span class="brand-icon">✦</span><span>星火同学<small>SPARK FOR ALL</small></span></a><nav aria-label="主导航"><button :class="{selected:page==='home'}" @click="page='home'">认识星火</button><button :class="{selected:page==='learn'}" @click="start()">学习空间</button><button @click="showImpact">公益足迹</button></nav><span class="welfare">微光成炬 · 公益学习计划</span></header>
 <div v-if="health?.mode==='demo'" class="mode-banner" role="status">离线演示模式：讲解由有限的分数演示引擎生成。资料搜索仍调用真实 AnySearch，数字人需单独连接。</div>
 <div v-else-if="health&&!health.llm_configured" class="mode-banner" role="status">学习模型尚未连接。可以浏览学习空间；生成讲解需要管理员配置模型服务。</div>
 <p v-if="error" class="error global-error" role="alert">{{error}} <button @click="error=''" aria-label="关闭错误提示">×</button></p>
 <main v-if="page==='home'" class="home">
  <section class="hero"><div class="hero-copy"><span class="eyebrow">每一点好奇，都有光</span><h1>不懂，没关系。<br><em>我们换种方法。</em></h1><p>让每一个孩子，都拥有一位<br>愿意耐心等待他的老师。</p><div class="hero-actions"><button class="primary" @click="start()" :disabled="busy">开始一起学习 <span>↗</span></button><span class="small">无需注册 · 匿名探索</span></div><label class="grade">我在读 <select v-model.number="grade" :disabled="!!state"><option :value="4">小学四年级</option><option :value="5">小学五年级</option><option :value="6">小学六年级</option></select></label></div>
   <div class="hero-art" aria-label="从困惑到理解的学习旅程"><span class="orbit one"></span><span class="orbit two"></span><div class="art-star">✦</div><div class="thought question">“为什么它们一样大？”</div><div class="fraction-card"><FractionVisual/><span>换个角度，就能看见答案。</span></div><div class="thought encouragement">慢慢来，你正在进步 ☀</div><span class="art-caption">好奇心，是学习的第一束光。</span></div>
  </section>
  <section class="topic-section"><div class="section-heading"><div><span class="eyebrow">从一个小问题开始</span><h2>今天，想探索什么？</h2></div><span class="small">数学与科学 · 适合四至六年级</span></div><div class="topic-grid"><button class="topic-card peach" @click="start('为什么 1/2 和 2/4 一样大？')"><span class="topic-symbol">½</span><span class="tag">数学 · 分数</span><h3>半块披萨的秘密</h3><p>为什么 1/2 和 2/4 一样大？</p><span class="arrow">一起想一想 ↗</span></button><button class="topic-card blue" @click="start('为什么月亮会有圆缺变化？')"><span class="topic-symbol">☾</span><span class="tag">科学 · 天文</span><h3>月亮的变身日记</h3><p>月亮真的会变大变小吗？</p><span class="arrow">带着好奇出发 ↗</span></button><button class="topic-card green" @click="start('植物为什么需要阳光？')"><span class="topic-symbol">☘</span><span class="tag">科学 · 自然</span><h3>一片叶子的午餐</h3><p>植物为什么需要阳光？</p><span class="arrow">发现身边的科学 ↗</span></button></div></section>
  <section class="mission"><span class="mission-star">✦</span><div><h2>资源有远近，好奇心没有。</h2><p>为教育资源不足地区的孩子，多点亮一盏学习的灯。星火是 AI 学习伙伴，帮助探索与理解，也鼓励孩子向身边的老师和家长求助。</p></div></section>
 </main>
 <main v-else-if="page==='learn'" class="learning">
  <div class="room-heading"><div><span class="eyebrow">我的学习空间 · 小学{{state?.grade}}年级</span><h1>{{current?.topic??'你好，今天想了解什么？'}}</h1></div><div class="room-controls"><label><input type="checkbox" v-model="textOnly"> 纯文字模式</label><button class="secondary" @click="page='summary'">学习小结 ↗</button></div></div>
  <div class="learning-grid"><TeacherAvatar ref="teacher" :text="speech" :text-only="textOnly"/>
   <section class="chat-panel" aria-label="学习对话"><div class="chat-top"><b>一起想，一起学</b><span class="pill" v-if="current">{{strategies[current.strategy]}}</span></div>
    <div class="conversation" ref="conversation" role="log" aria-live="polite" aria-relevant="additions">
     <div v-if="!messages.length" class="welcome-message"><span class="tiny-star">✦</span><h2>你的问题，我认真听。</h2><p>我是星火老师，一位 AI 学习伙伴。遇到不懂的地方，我们就换个方法。</p><button @click="text='为什么 1/2 和 2/4 一样大？'">试着问：为什么 1/2 和 2/4 一样大？</button><p class="small">只分享学习问题，不要填写姓名、学校、地址或联系方式。</p></div>
     <article v-for="(message,index) in messages" :key="index" :class="['message',message.role]"><span class="message-label">{{message.role==='teacher'?'✦ 星火老师 · AI 生成':'我的问题'}}</span><p>{{message.text}}</p><FractionVisual v-if="message.visual==='fractions'"/><p v-for="warning in message.warnings" class="notice">{{warningLabels[warning]??'服务暂时不可用'}}</p><details v-if="message.sources.length" class="sources"><summary>参考资料 · {{message.sources.length}} 个检索来源</summary><p class="small">以下为实际检索资料，不代表已经独立核实；上方讲解为 AI 生成。</p><div v-for="source in message.sources" :key="source.id"><a :href="source.url" target="_blank" rel="noopener noreferrer">{{source.title}} ↗</a><p>{{source.snippet}}</p><small>检索时间：{{new Date(source.retrieved_at).toLocaleString('zh-CN')}}</small></div></details></article>
     <p v-if="busy" role="status" class="thinking">✦ 正在想一个适合你的讲法…</p>
    </div>
    <div class="learning-actions"><button @click="send('again')" :disabled="busy||!current">↻ 再讲一次</button><button @click="send('example')" :disabled="busy||!current">☀ 换个例子</button><button @click="send('understood')" :disabled="busy||!current">✓ 我懂了</button><button @click="send('quiz')" :disabled="busy||!current">✎ 考考我</button></div>
    <form @submit.prevent="send('ask')" class="composer"><label for="question" class="sr-only">写下你的问题</label><textarea id="question" v-model="text" maxlength="1000" placeholder="把你的好奇写在这里…" rows="2" :disabled="busy" @keydown="questionKey"></textarea><div><button v-if="SpeechRecognition" type="button" @click="voice" :disabled="busy" :aria-pressed="listening">{{listening?'停止录音':'语音输入'}}</button><span v-else class="small">当前浏览器可使用文字输入</span><button class="primary" :disabled="busy||!text.trim()">发送 ↗</button></div><small v-if="SpeechRecognition">语音由浏览器服务识别，可能发送至其服务商；识别后可修改，再发送。</small></form>
   </section>
  </div>
  <section v-if="current?.quiz" class="quiz-panel"><div><span class="eyebrow">不计分的小挑战</span><h2>{{current.quiz.question}}</h2><p class="small">答错也没关系，我们一起找到原因。</p></div><div class="quiz-options" v-if="current.quiz.options.length"><button v-for="option in current.quiz.options" @click="send('answer',option)" :disabled="busy">{{option}}</button></div><form v-else @submit.prevent="send('answer',answer)"><label for="answer">我的答案</label><input id="answer" v-model="answer" maxlength="100"><button class="primary" :disabled="busy||!answer.trim()">试试看</button></form><button class="text-button" @click="send('skip')" :disabled="busy">先跳过，换个话题</button></section>
  <p class="privacy-note">匿名学习 · 会话最多保留 1 小时（活动时续期） · <button @click="end" :disabled="busy">结束并删除本次学习</button></p>
 </main>
 <main v-else-if="page==='summary'" class="summary-page"><span class="eyebrow">每一小步，都算数</span><h1>今天的探索小记</h1><p>理解需要时间。这里记录你的尝试，不是考试成绩或掌握程度认证。</p><div class="stats"><div><b>{{topics.length}}</b><span>探索的话题</span></div><div><b>{{topics.reduce((n,t)=>n+t.attempts,0)}}</b><span>讲解尝试</span></div><div><b>{{topics.reduce((n,t)=>n+t.completed_quizzes,0)}}</b><span>完成的小练习</span></div></div><div class="summary-topics"><article v-for="topic in topics"><span class="pill">{{states[topic.understanding]}}</span><h2>{{topic.topic}}</h2><p>{{topic.self_reported?'你说自己觉得更明白了。':'可以尝试用自己的话讲给家人听。'}}</p><p>{{topic.understanding==='needs_reinforcement'?'下次值得再看看这个知识点。':'让我们在新的例子里再试一次。'}}</p><small>{{topic.attempts}} 次讲解尝试 · {{topic.completed_quizzes}} 次小练习</small></article><p v-if="!topics.length">还没有学习记录，从一个小问题开始吧。</p></div><h2>下一次，可以探索…</h2><button class="secondary" @click="start('为什么月亮会有圆缺变化？')">月亮为什么有圆缺？ ↗</button> <button class="primary" @click="page='learn'">回到学习空间</button></main>
 <main v-else class="impact-page"><span class="eyebrow">微光成炬</span><h1>让每一次好奇，被看见。</h1><p>公开、透明地记录学习参与情况，不把使用量等同于教育成效。</p><section v-for="mode in (['live','demo'] as const)"><h2>{{mode==='live'?'真实使用记录':'演示模式记录'}} <span class="small">{{mode==='live'?'来自 live 模式':'仅用于开发和功能演示'}}</span></h2><div class="stats"><div v-for="(label,key) in {sessions:'学习会话',interactions:'学习互动',alternative_explanations:'换一种讲法',topics_explored:'话题探索次数',self_reported_improvements:'自报理解改善'}"><b>{{impact?.[mode][key]??0}}</b><span>{{label}}</span></div></div></section><p class="notice">{{impact?.note}}</p><p>没有收集学生真实姓名、学校或精确位置。记录不用于排名，也不用于建立长期儿童画像。</p></main>
 <footer><div><b>✦ 星火同学</b><span>让学习，多一点耐心。</span></div><p>技术支持：<a href="https://www.anysearch.com/" target="_blank" rel="noopener noreferrer">AnySearch</a> · <a href="https://xingyun3d.com/" target="_blank" rel="noopener noreferrer">魔珐星云 Xingyun3D</a><small>AI 可能出错，重要知识请和老师一起核对。</small></p></footer>
</template>
