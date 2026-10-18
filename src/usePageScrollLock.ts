import {useEffect} from 'react';

// Reference-counted across nested dialogs; fixed body also works in mobile WebViews.
let depth=0;
let restore:undefined|(()=>void);
export function lockPageScroll(){
 if(depth++===0){
  const body=document.body,html=document.documentElement,x=window.scrollX,y=window.scrollY;
  const bodyStyle=body.getAttribute('style'),htmlStyle=html.getAttribute('style');
  body.style.position='fixed';body.style.top=`-${y}px`;body.style.left=`-${x}px`;body.style.width='100%';body.style.overflow='hidden';html.style.overflow='hidden';
  restore=()=>{if(bodyStyle===null)body.removeAttribute('style');else body.setAttribute('style',bodyStyle);if(htmlStyle===null)html.removeAttribute('style');else html.setAttribute('style',htmlStyle);window.scrollTo(x,y)};
 }
 let released=false;
 return ()=>{if(released)return;released=true;if(--depth===0){restore?.();restore=undefined}};
}
export function usePageScrollLock(active=true){useEffect(()=>active?lockPageScroll():undefined,[active])}
