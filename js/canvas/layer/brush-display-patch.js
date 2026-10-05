/* SPB-93 owner09-08: avoid full 4096 SOURCE texture uploads during Brush.
 * This is a disposable display surface, never an editable pixel authority. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;if(root)root.SPBBrushDisplayPatch=api;})(typeof window==='object'?window:globalThis,function(){
 'use strict';
 let bounds=null,surface=null;
 function expand(rect){
  if(!rect)return null;
  if(!bounds)return {...rect};
  const x=Math.min(bounds.x,rect.x),y=Math.min(bounds.y,rect.y);
  return {x,y,width:Math.max(bounds.x+bounds.width,rect.x+rect.width)-x,height:Math.max(bounds.y+bounds.height,rect.y+rect.height)-y};
 }
 function opaque(pixels){for(let i=3;i<pixels.data.length;i+=4)if(pixels.data[i]!==255)return false;return true;}
 function show(pixels,rect,source){
  // An opaque composite can cover the original exactly. A transparent patch
  // cannot conceal old pixels below it, so it must use the existing path.
  if(!source?.parentElement||source.style.opacity==='0'||!opaque(pixels))return false;
  if(!surface){surface=source.ownerDocument.createElement('canvas');surface.id='spbBrushDisplayPatch';surface.setAttribute('aria-hidden','true');surface.style.cssText='position:absolute;pointer-events:none;z-index:2;';source.parentElement.append(surface);}
  if(surface.width!==pixels.width)surface.width=pixels.width;
  if(surface.height!==pixels.height)surface.height=pixels.height;
  surface.getContext('2d',{willReadFrequently:true}).putImageData(pixels,0,0);
  surface.style.left=(100*rect.x/source.width)+'%';surface.style.top=(100*rect.y/source.height)+'%';
  surface.style.width=(100*rect.width/source.width)+'%';surface.style.height=(100*rect.height/source.height)+'%';
  bounds={...rect};return true;
 }
 function clear(){surface?.remove();surface=null;bounds=null;}
 return Object.freeze({expand,opaque,show,clear});
});
