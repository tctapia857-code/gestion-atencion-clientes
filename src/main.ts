import { Component, OnDestroy, isDevMode, signal } from '@angular/core';
import { bootstrapApplication } from '@angular/platform-browser';
import { localRequest } from './local-api';
interface Ticket { id: number; name: string; desk_id: number | null; }
interface Desk { id: number; ticket: Ticket | null; }
interface State { waiting: Ticket[]; desks: Desk[]; completed: number; recent: Ticket[]; }
@Component({selector:'app-root',standalone:true,templateUrl:'./app.html'})
class App implements OnDestroy {
  readonly localMode = !isDevMode();
  private request(path: string, options?: RequestInit) {
    return this.localMode ? localRequest(path, options) : fetch('/api/' + path, options);
  }
  state = signal<State>({waiting:[],desks:[1,2,3,4].map(id=>({id,ticket:null})),completed:0,recent:[]});
  name = signal(''); error = signal(''); notice = signal(''); busy = signal(false); connected = signal(false);
  private refreshId=0;
  private timer = setInterval(()=>void this.refresh(), 3000);
  constructor(){ void this.refresh(); }
  ngOnDestroy(){clearInterval(this.timer);}
  turn(id:number){return 'A-'+String(id).padStart(3,'0');}
  active(){return this.state().desks.filter(d=>d.ticket).length;}
  async refresh(){
    const id=++this.refreshId;
    try {const response=await this.request('state'); if(!response.ok)throw new Error(); const state=await response.json() as State;
      if(id===this.refreshId){this.state.set(state);this.connected.set(true);}
    } catch {if(id===this.refreshId)this.connected.set(false);}
  }
  async action(path:string,body:object={}){
    if(this.busy())return;
    this.busy.set(true);this.error.set('');this.notice.set('');
    try {
      const response=await this.request(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      const data=await response.json(); if(!response.ok)throw new Error(data.error || 'No se pudo realizar la operación.');
      if(path==='tickets'){this.name.set('');this.notice.set('Turno '+this.turn(data.id)+' generado para '+data.name+'.');}
      else this.notice.set(data.message);
      await this.refresh();
    } catch(e){this.error.set(e instanceof Error?e.message:'No se pudo conectar al servidor.');await this.refresh();}
    finally{this.busy.set(false);}
  }
  register(event:Event){event.preventDefault();void this.action('tickets',{name:this.name()});}
}
bootstrapApplication(App).catch(console.error);
