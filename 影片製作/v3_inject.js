/* ===== 第三版錄影用注入（只插進 影片製作/site_v3 的副本，原始 m.html 不含這段） =====
   由 make_video_v3.py 插在主程式封閉區塊的結尾，才拿得到 buildReport、$ 等內部函式。
   內容：公司標誌、案名大字、案名列、案場按鈕做像素馬賽克（範圍同第一版）；
   日報表的「工地地點」欄打馬賽克；提供錄影程式呼叫的介面。 */
(function(){
  // ---- 像素馬賽克（與第一版 sim.js 相同） ----
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
    '#pmeta,#ptags,#lat,#lon,#stainfo{filter:url(#pxS)}';
  document.head.appendChild(st);

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

  // ---- 日報表：只把「工地地點」的名稱打馬賽克（座標、時間、數據照留） ----
  const _br=buildReport;
  buildReport=function(){
    const f=$("rpFrame");
    f.onload=function(){
      try{
        const doc=f.contentDocument, metas=doc.querySelectorAll(".meta");
        const b=function(t){ return '<span style="filter:blur(7px)">'+t+'</span>'; };
        if(metas[0]) metas[0].innerHTML=metas[0].innerHTML
          .replace(/工地地點：([^｜<]+)/,'工地地點：'+b("$1"))
          .replace(/座標：([^｜<]+)/,'座標：'+b("$1"));
        if(metas[1]) metas[1].innerHTML=b(metas[1].innerHTML);   // 資料來源含測站名稱，整列打馬賽克
      }catch(e){}
    };
    _br();
  };

  // ---- 給錄影程式呼叫的介面 ----
  window.SIMV3={
    report:function(){ buildReport(); return true; },
    rscroll:function(frac){
      const w=$("rpFrame").contentWindow; if(!w) return false;
      const h=w.document.documentElement.scrollHeight-w.innerHeight;
      w.scrollTo({top:Math.max(0,h*frac),behavior:"smooth"}); return true;
    },
    close:function(){ ["ovRep","ovRadar","ovTbl","ovNote","ovTy"].forEach(function(id){ $(id).classList.add("hide"); }); return true; }
  };
})();
