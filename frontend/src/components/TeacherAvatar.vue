<script setup lang="ts">
import { ref,onBeforeUnmount,watch } from 'vue'
import { api } from '../services/api'
import { Avatar,type AvatarState } from '../services/avatar'
const props=defineProps<{text:string;textOnly:boolean}>()
const status=ref<AvatarState>('off'),error=ref(''),connecting=ref(false)
const avatar=new Avatar(s=>status.value=s)
const labels:Record<AvatarState,string>={off:'文字学习也很精彩',loading:'正在加载数字人',connecting:'正在连接星火老师',idle:'我在听，慢慢说',speaking:'星火老师正在讲解',error:'数字人暂时不可用'}
async function connect(){error.value='';connecting.value=true;try{const config=await api<Record<string,string>>('/avatar/config');await avatar.connect(config,'#teacher-canvas')}catch(e){error.value=(e as Error).message;status.value='error'}finally{connecting.value=false}}
watch(()=>props.text,text=>{if(!props.textOnly && status.value==='idle'){try{avatar.speak(text)}catch{error.value='语音播放失败，可以继续阅读文字。'}}})
watch(()=>props.textOnly,only=>{if(only)avatar.destroy()})
onBeforeUnmount(()=>avatar.destroy())
defineExpose({interrupt:()=>avatar.interrupt()})
</script>
<template>
  <section class="teacher-panel" aria-label="星火老师数字人">
    <div class="teacher-top"><span class="pill">✦ 星火老师 · AI</span><span class="small">陪你一起探索</span></div>
    <div id="teacher-canvas" :class="{active:status==='idle'||status==='speaking'}"></div>
    <div v-if="!['idle','speaking'].includes(status)" class="teacher-placeholder">
      <div class="sun-mark" aria-hidden="true">✦</div><h2>每个“为什么”，<br>都值得慢慢解答。</h2>
      <p>{{ labels[status] }}</p><p class="small">3D 数字人尚未连接 · 当前使用文字模式</p>
      <button v-if="!textOnly" class="secondary" @click="connect" :disabled="connecting">{{connecting?'连接中…':'连接 3D 星火老师'}}</button>
    </div>
    <div v-else class="teacher-status" role="status">● {{labels[status]}} <button @click="avatar.interrupt()">暂停讲解</button></div>
    <p v-if="error" class="notice" role="status">{{error}}</p>
    <p class="teacher-caption">不用着急，也不用怕答错。<br>我们可以换一种方法，再试一次。</p>
  </section>
</template>
