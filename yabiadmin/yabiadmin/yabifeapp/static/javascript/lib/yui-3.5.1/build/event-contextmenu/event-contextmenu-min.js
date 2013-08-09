/*
YUI 3.5.1 (build 22)
Copyright 2012 Yahoo! Inc. All rights reserved.
Licensed under the BSD License.
http://yuilibrary.com/license/
*/
YUI.add("event-contextmenu",function(b){var k=b.Event,m=b.DOM,h=b.UA,l=b.UA.os,a=h.ie,c=h.gecko,i=h.webkit,d=h.opera,e=(l==="windows"),f=(l==="macintosh"),j={},g={on:function(r,q,p,o){var n=[];n.push(k._attach(["contextmenu",function(t){t.preventDefault();var u=b.stamp(r),s=j[u];if(s){t.clientX=s.clientX;t.clientY=s.clientY;t.pageX=s.pageX;t.pageY=s.pageY;delete j[u];}p.fire(t);},r]));n.push(r[o?"delegate":"on"]("keydown",function(L){var M=this.getDOMNode(),F=L.shiftKey,z=L.keyCode,I=(F&&z==121),A=(e&&z==93),u=L.ctrlKey,D=(z===77),E=(f&&(i||c)&&u&&F&&L.altKey&&D),v=(f&&d&&u&&F&&D),H=0,G=0,K,J,t,s,w,C,B;if((e&&(I||A))||(E||v)){if(((a||(e&&(c||d)))&&I)||v){L.preventDefault();}w=m.getXY(M);C=w[0];B=w[1];K=m.docScrollX();J=m.docScrollY();if(!b.Lang.isUndefined(C)){H=(C+(M.offsetWidth/2))-K;G=(B+(M.offsetHeight/2))-J;}t=H+K;s=G+J;if(A||(e&&i&&I)){j[b.stamp(r)]={clientX:H,clientY:G,pageX:t,pageY:s};}if(((a||(e&&(c||d)))&&I)||f){L.clientX=H;L.clientY=G;L.pageX=t;L.pageY=s;p.fire(L);}}},o));q._handles=n;},detach:function(p,o,n){b.each(o._handles,function(q){q.detach();});}};g.delegate=g.on;g.detachDelegate=g.detach;k.define("contextmenu",g,true);},"3.5.1",{requires:["event-synthetic","dom-screen"]});