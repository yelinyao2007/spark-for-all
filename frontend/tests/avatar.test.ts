import { expect,test,vi } from 'vitest'
import { Avatar,escapeSpeech } from '../src/services/avatar'
test('LLM text cannot inject avatar SSML actions',()=>{expect(escapeSpeech('<speak>& "hi"')).toBe('&lt;speak&gt;&amp; &quot;hi&quot;')})
test('adapter initializes, interrupts, speaks and releases official SDK',async()=>{
 const sdk={init:vi.fn(async()=>{}),speak:vi.fn(),interactiveidle:vi.fn(),destroy:vi.fn()}
 vi.stubGlobal('window',{isSecureContext:true,XmovAvatar:class{constructor(){return sdk}}})
 vi.stubGlobal('document',{createElement:()=>({getContext:()=>({})})})
 const changed=vi.fn(),avatar=new Avatar(changed)
 await avatar.connect({appId:'test-only',appSecret:'test-only'},'#teacher-canvas')
 avatar.speak('<action>hello')
 expect(sdk.speak).toHaveBeenCalledWith('&lt;action&gt;hello',true,true)
 avatar.interrupt();expect(sdk.interactiveidle).toHaveBeenCalledTimes(2)
 avatar.destroy();expect(sdk.destroy).toHaveBeenCalledOnce()
 expect(changed).toHaveBeenCalledWith('idle')
 vi.unstubAllGlobals()
})
test('switching to text mode cancels a pending SDK initialization',async()=>{
 const sdk={init:vi.fn(()=>new Promise<void>(()=>{})),speak:vi.fn(),interactiveidle:vi.fn(),destroy:vi.fn()}
 vi.stubGlobal('window',{isSecureContext:true,XmovAvatar:class{constructor(){return sdk}}})
 vi.stubGlobal('document',{createElement:()=>({getContext:()=>({})})})
 const avatar=new Avatar(vi.fn())
 const pending=avatar.connect({appId:'test-only',appSecret:'test-only'},'#teacher-canvas')
 avatar.destroy()
 await pending
 expect(sdk.destroy).toHaveBeenCalledOnce()
 vi.unstubAllGlobals()
})
test('SDK connection errors release resources',async()=>{
 let options:Record<string,unknown>={}
 const sdk={init:vi.fn(async()=>{}),speak:vi.fn(),interactiveidle:vi.fn(),destroy:vi.fn()}
 vi.stubGlobal('window',{isSecureContext:true,XmovAvatar:class{constructor(o:Record<string,unknown>){options=o;return sdk}}})
 vi.stubGlobal('document',{createElement:()=>({getContext:()=>({})})})
 const changed=vi.fn(),avatar=new Avatar(changed)
 await avatar.connect({appId:'test-only',appSecret:'test-only'},'#teacher-canvas')
 ;(options.onStatusChange as (n:number)=>void)(3)
 await Promise.resolve()
 expect(sdk.destroy).toHaveBeenCalledOnce()
 expect(changed).toHaveBeenLastCalledWith('error')
 vi.unstubAllGlobals()
})
