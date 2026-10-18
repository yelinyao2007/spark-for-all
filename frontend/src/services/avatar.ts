// Official XmovAvatar integration. No fabricated token exchange or SDK methods.
// Contract: https://www.xingyun3d.com/developers/52-183
export type AvatarState = 'off'|'loading'|'connecting'|'idle'|'speaking'|'error'
export interface AvatarSDK { init(options:{onDownloadProgress:(progress:number)=>void}):Promise<void>; speak(text:string,start:boolean,end:boolean):void; interactiveidle():void; destroy():void }
declare global { interface Window { XmovAvatar?:new (options:Record<string,unknown>)=>AvatarSDK } }
const SDK_URL='https://media.xingyun3d.com/xingyun3d/general/litesdk/xmovAvatar@latest.js'
export function escapeSpeech(text:string) { return text.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&apos;') }
export class Avatar {
  private sdk?:AvatarSDK
  private generation=0
  private timer?:ReturnType<typeof setTimeout>
  private cancelInit?:()=>void
  constructor(private changed:(state:AvatarState)=>void) {}
  async connect(config:Record<string,string>,containerId:string) {
    this.destroy()
    const generation=++this.generation
    if(!window.isSecureContext || !document.createElement('canvas').getContext('webgl2')) throw new Error('此浏览器暂不支持数字人，请使用文字模式。')
    this.changed('loading')
    if(!window.XmovAvatar) await new Promise<void>((resolve,reject)=>{
      const script=document.createElement('script');script.src=SDK_URL;script.async=true
      const timer=setTimeout(()=>{script.remove();reject(new Error('数字人资源加载超时'))},20000)
      script.onload=()=>{clearTimeout(timer);resolve()}
      script.onerror=()=>{clearTimeout(timer);script.remove();reject(new Error('数字人资源加载失败'))}
      document.head.appendChild(script)
    })
    if(generation!==this.generation)return
    if(!window.XmovAvatar)throw new Error('数字人 SDK 不可用')
    this.changed('connecting')
    const fail=()=>queueMicrotask(()=>{if(generation===this.generation){this.destroy();this.changed('error')}})
    const sdk=new window.XmovAvatar({...config,containerId,enableLogger:false,
      onMessage:(message:{code:number})=>{if(generation===this.generation && message.code && ![50002,50003].includes(message.code)){fail()}},
      onStatusChange:(status:number)=>{if(generation===this.generation && [1,3,4,7].includes(status))fail()},
      onVoiceStateChange:(status:string)=>{if(generation===this.generation)this.changed(['start','voice_start'].includes(status)?'speaking':'idle')}
      // Keep SDK's default subtitle_on/off renderer for synchronized subtitles.
    })
    this.sdk=sdk
    try {
      await Promise.race([sdk.init({onDownloadProgress:()=>{}}),new Promise<never>((_,reject)=>{this.cancelInit=()=>reject(new Error('连接已取消'));this.timer=setTimeout(()=>reject(new Error('数字人连接超时')),45000)})])
      clearTimeout(this.timer);this.cancelInit=undefined
      if(generation!==this.generation){sdk.destroy();return}
      this.changed('idle')
    }catch(error){if(generation!==this.generation)return;this.destroy();this.changed('error');throw error}
  }
  speak(text:string){if(this.sdk){this.sdk.interactiveidle();this.sdk.speak(escapeSpeech(text),true,true)}}
  interrupt(){this.sdk?.interactiveidle();if(this.sdk)this.changed('idle')}
  destroy(){++this.generation;this.cancelInit?.();this.cancelInit=undefined;clearTimeout(this.timer);this.sdk?.destroy();this.sdk=undefined;this.changed('off')}
}
