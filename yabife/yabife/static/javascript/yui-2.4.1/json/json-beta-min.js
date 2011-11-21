/*
Copyright (c) 2007, Yahoo! Inc. All rights reserved.
Code licensed under the BSD License:
http://developer.yahoo.net/yui/license.txt
version: 2.4.1
*/
YAHOO.namespace("lang");YAHOO.lang.JSON={parse:function(s,filter){var j;function walk(k,v){var i,n;if(v&&typeof v==="object"){for(i in v){if(YAHOO.lang.hasOwnProperty.apply(v,[i])){n=walk(i,v[i]);if(n!==undefined){v[i]=n;}}}}return filter(k,v);}if(/^[\],:{}\s]*$/.test(s.replace(/\\./g,"@").replace(/"[^"\\\n\r]*"|true|false|null|-?\d+(?:\.\d*)?(:?[eE][+\-]?\d+)?/g,"]").replace(/(?:^|:|,)(?:\s*\[)+/g,""))){j=eval("("+s+")");return typeof filter==="function"?walk("",j):j;}throw new SyntaxError("parseJSON");},stringify:function(D,J,H){var F=YAHOO.lang,A=/["\\\x00-\x1f]/g,E={"\b":"\\b","\t":"\\t","\n":"\\n","\f":"\\f","\r":"\\r","\"":"\\\"","\\":"\\\\"},C=[];function B(M){if(!E[M]){var L=M.charCodeAt();E[M]="\\u00"+Math.floor(L/16).toString(16)+(L%16).toString(16);}return E[M];}function G(L){return L<10?"0"+L:L;}function K(L){return"\""+L.replace(A,B)+"\"";}function I(L,S,Q){var V=typeof L,O,P,N,M,T,U,R;if(V==="string"){return K(L);}if(V==="boolean"||L instanceof Boolean){return String(L);}if(V==="number"||L instanceof Number){return isFinite(L)?String(L):"null";}if(L instanceof Date){return["\"",L.getUTCFullYear(),"-",G(L.getUTCMonth()+1),"-",G(L.getUTCDate()),"T",G(L.getUTCHours()),":",G(L.getUTCMinutes()),":",G(L.getUTCSeconds()),"Z\""].join("");}if(F.isArray(L)){for(O=0,P=C.length;O<P;++O){if(C[O]===L){return"null";}}C[C.length]=L;R=[];if(Q>0){for(O=0,P=L.length;O<P;++O){R[O]=I(L[O],S,Q-1);}}C.pop();return"["+R.join(",")+"]";}if(V==="object"&&L){for(O=0,P=C.length;O<P;++O){if(C[O]===L){return"null";}}C[C.length]=L;R=[];if(Q>0){if(S){for(O=0,N=0,P=S.length;O<P;++O){T=L[S[O]];U=typeof T;if(U!=="undefined"&&U!=="function"){R[N++]=K(S[O])+":"+I(T,S,Q-1);}}}else{N=0;for(M in L){if(typeof M==="string"&&F.hasOwnProperty(L,M)){T=L[M];U=typeof T;if(U!=="undefined"&&U!=="function"){R[N++]=K(M)+":"+I(T,S,Q-1);}}}}}C.pop();return"{"+R.join(",")+"}";}return"null";}H=H>=0?H:1/0;return I(D,J,H);}};YAHOO.register("json",YAHOO.lang.JSON,{version:"2.4.1",build:"742"});