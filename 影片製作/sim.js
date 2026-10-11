/* ===== 錄影用模擬（只插進「影片製作/site/demo.html」這份副本，原始程式不含這段） =====
   由 make_video.py --bake 插在主程式封閉區塊的結尾、啟動之前，才拿得到 render、siteI 等內部變數。
   模擬只改「送進畫面前的數據」，研判卡、降雨快報、逐時趨勢、跑馬燈全部照原程式自己算。 */
(function(){
  // ---- 像素馬賽克：公司標誌、案名大字、案名列、案場按鈕 ----
  function pxFilter(id,cell){
    const h=cell/2|0, c=(cell/2|0)-1;
    return '<filter id="'+id+'" x="0" y="0" width="1" height="1">'+
      '<feFlood x="'+c+'" y="'+c+'" height="2" width="2"/>'+
      '<feComposite width="'+cell+'" height="'+cell+'"/><feTile result="a"/>'+
      '<feComposite in="SourceGraphic" in2="a" operator="in"/>'+
      '<feMorphology operator="dilate" radius="'+h+'"/></filter>';
  }
  const svg=document.createElement("div");
  svg.innerHTML='<svg width="0" height="0" style="position:absolute"><defs>'+pxFilter("pxL",18)+pxFilter("pxS",9)+'</defs></svg>';
  document.body.appendChild(svg.firstChild);
  const st=document.createElement("style");
  st.textContent=
    '#logo,#logoFb,.bt .t1 .nmz{filter:url(#pxL)}'+
    '.bt .t1 .nmz{display:inline-block}'+
    '#pname,#siteind button{filter:url(#pxS)}'+
    '#simBadge{position:fixed;top:10px;left:50%;transform:translateX(-50%);z-index:9999;display:none;'+
      'background:#b3261e;color:#fff;font:700 22px "Microsoft JhengHei",sans-serif;padding:7px 22px;'+
      'border-radius:9px;box-shadow:0 0 0 3px #ffd54a,0 6px 24px #000a;letter-spacing:1px}'+
    'body.sim #simBadge{display:block}'+
    '.hl{outline:5px solid #ffd54a!important;outline-offset:4px;animation:hlp 1s ease-in-out infinite;position:relative;z-index:50}'+
    '@keyframes hlp{50%{outline-color:rgba(255,213,74,.2)}}';
  document.head.appendChild(st);
  const bd=document.createElement("div"); bd.id="simBadge"; bd.textContent="模擬情境　示範用，非實測數據";
  document.body.appendChild(bd);

  function nameSpan(){
    const t1=document.querySelector(".bt .t1"); if(!t1) return null;
    let s=t1.querySelector(".nmz");
    if(!s){
      s=document.createElement("span"); s.className="nmz";
      const tn=t1.firstChild;
      if(tn&&tn.nodeType===3){ s.textContent=tn.nodeValue; t1.replaceChild(s,tn); }
      else t1.insertBefore(s,t1.firstChild);
    }
    return s;
  }
  nameSpan();
  setBrandName=function(nm){ const s=nameSpan(); if(s) s.textContent=nm; document.title=nm+" 氣象監測"; };

  // ---- 模擬數據 ----
  let SIMS=null;
  function idxNow(T){ const now=Date.now(); let k=0; T.forEach(function(t,i){ if(new Date(t).getTime()<=now) k=i; }); return k; }
  function applySim(S,om,cwa){
    om=JSON.parse(JSON.stringify(om)); cwa=JSON.parse(JSON.stringify(cwa||{}));
    const H=om.hourly, iN=idxNow(H.time);
    function put(arr,map){ if(!arr||!map) return; for(const k in map){ const i=iN+(+k); if(i>=0&&i<arr.length) arr[i]=map[k]; } }
    put(H.precipitation,S.hourRain); if(H.rain) put(H.rain,S.hourRain);
    put(H.wind_gusts_10m,S.hourGust); put(H.wind_speed_10m,S.hourWind);
    const M=om.minutely_15;
    if(S.m15&&M&&M.time){
      const now=Date.now(); let k=M.time.length;
      for(let i=0;i<M.time.length;i++){ if(new Date(M.time[i]).getTime()>now){ k=i; break; } }
      S.m15.forEach(function(v,j){ const i=k-1+j; if(i>=0&&i<M.precipitation.length) M.precipitation[i]=v; });
    }
    if(S.cur) Object.assign(om.current,S.cur);
    if(S.rain){
      const o=cwa.rain||{name:"模擬",km:1};
      cwa.rain=Object.assign({},o,{time:new Date().toISOString()},S.rain);
      const D=om.daily, now=new Date();
      const ds=new Date(now.getTime()-now.getTimezoneOffset()*60000).toISOString().slice(0,10);
      const di=D.time.indexOf(ds); if(di>=0&&S.rain.day!=null) D.precipitation_sum[di]=S.rain.day;
    }
    if(S.wx){
      const o=cwa.wx||{name:"模擬",km:1,temp:null,rh:null,wdir:null,uv:null};
      cwa.wx=Object.assign({},o,{time:new Date().toISOString()},S.wx);
    }
    return [om,cwa];
  }
  const _render=render;
  render=function(lat,lon,om,place,cwa,quake,ty){
    const on=!!(SIMS&&SIMS.site===siteI);
    if(on){ const r=applySim(SIMS,om,cwa); om=r[0]; cwa=r[1]; }
    document.body.classList.toggle("sim",on);
    _render(lat,lon,om,place,cwa,quake,ty);
  };
  const _lmr=loadMiniRadar;
  loadMiniRadar=function(){
    if(SIMS&&SIMS.site===siteI&&SIMS.radar){
      $("rdmini").src=SIMS.radar;
      $("rdtime").textContent="模擬回波（示範用）";
    } else _lmr();
  };

  // ---- 給錄影程式呼叫的介面 ----
  function rect(sel){
    const e=document.querySelector(sel); if(!e) return null;
    const r=e.getBoundingClientRect(); return [r.left,r.top,r.width,r.height];
  }
  window.SIM={
    ready:function(){ return !!siteCache[siteI] && !siteBusy; },
    stop:function(){ if(siteTimer){ clearInterval(siteTimer); siteTimer=null; } return true; },
    go:function(i){ return showSite(i,true).then(function(){ return siteI; }); },
    prep:function(S){ SIMS=S; return true; },
    set:function(S){ SIMS=S; return SIM.redraw(); },
    redraw:function(){
      const c=siteCache[siteI]; if(!c) return false; const d=c.d;
      render(d.lat,d.lon,d.om,d.place,d.cwa,d.quake,d.ty);
      $("pname").textContent=SITES[siteI].name;
      return true;
    },
    radar:function(u){ if(SIMS) SIMS.radar=u; loadMiniRadar(); return true; },
    hl:function(sel){
      document.querySelectorAll(".hl").forEach(function(e){ e.classList.remove("hl"); });
      if(sel) document.querySelectorAll(sel).forEach(function(e){ e.classList.add("hl"); });
      return true;
    },
    report:function(){ buildReport(); return true; },
    rscroll:function(frac){
      const w=$("rpFrame").contentWindow; if(!w) return false;
      const h=w.document.documentElement.scrollHeight-w.innerHeight;
      w.scrollTo({top:Math.max(0,h*frac),behavior:"smooth"}); return true;
    },
    close:function(){ ["ovRep","ovRadar","ovTbl","ovNote","ovTy"].forEach(function(id){ $(id).classList.add("hide"); }); return true; },
    rects:function(){
      const o={};
      ["#rain","#wind","#env","#quake","#alerts","#banner","#rdmain","#siteind","#ovRep .ovbox"].forEach(function(s){ o[s]=rect(s); });
      const cr=$("chartRain"); if(cr){ let p=cr; while(p&&p.parentElement&&!/(^|\s)g-/.test(p.className)) p=p.parentElement;
        const r=p.getBoundingClientRect(); o["chart"]=[r.left,r.top,r.width,r.height]; }
      const rd=$("rdmain"); if(rd){ let p=rd; while(p&&p.parentElement&&!/(^|\s)g-/.test(p.className)) p=p.parentElement;
        const r=p.getBoundingClientRect(); o["radar"]=[r.left,r.top,r.width,r.height]; }
      // 「GPS 座標 → 自動找最近測站」那一塊：經緯度欄、查詢、目前位置、測站列合起來
      const g=[$("lat").closest(".f"),$("lon").closest(".f"),$("go"),$("geo"),$("stainfo").closest(".f")]
        .filter(Boolean).map(function(e){ return e.getBoundingClientRect(); });
      if(g.length){ const x0=Math.min.apply(null,g.map(function(r){return r.left;})), y0=Math.min.apply(null,g.map(function(r){return r.top;})),
        x1=Math.max.apply(null,g.map(function(r){return r.right;})), y1=Math.max.apply(null,g.map(function(r){return r.bottom;}));
        o["gps"]=[x0,y0,x1-x0,y1-y0]; }
      o.vw=innerWidth; o.vh=innerHeight; return o;
    },
    nowcast:function(){ return (LAST&&LAST.kv)?LAST.kv.map(function(x){return x.join("：");}):[]; }
  };
})();
