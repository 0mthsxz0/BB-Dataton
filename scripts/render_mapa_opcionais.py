import json,textwrap,html
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
out=Path(__file__).resolve().parents[1]/'entregas';rows=json.loads((out/'mapa-opcionais.json').read_text(encoding='utf-8'))
W=1800;H=2700
im=Image.new('RGB',(W,H),'#f3f7fb');d=ImageDraw.Draw(im)
fontpath='C:/Windows/Fonts/arial.ttf';bold='C:/Windows/Fonts/arialbd.ttf'
f=lambda n,b=False:ImageFont.truetype(bold if b else fontpath,n)
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}"><rect width="100%" height="100%" fill="#f3f7fb"/>']
def rect(box,fill):
 d.rounded_rectangle(box,radius=12,fill=fill);x,y,x2,y2=box;svg.append(f'<rect x="{x}" y="{y}" width="{x2-x}" height="{y2-y}" rx="12" fill="{fill}"/>')
def tx(x,y,t,size=21,color='#243e53',b=False):
 d.text((x,y),t,font=f(size,b),fill=color);svg.append(f'<text x="{x}" y="{y+size}" font-family="Arial,sans-serif" font-size="{size}" font-weight="{700 if b else 400}" fill="{color}">{html.escape(t)}</text>')
def lines(x,y,text,width,size=21,color='#243e53',b=False):
 for line in textwrap.wrap(text,width=width):tx(x,y,line,size,color,b);y+=size+8
 return y
rect((24,20,1776,152),'#122e46');tx(52,43,'Coberturas opcionais: do sinal à recomendação',40,'white',True);tx(52,103,'21 itens | Guia, seção 10.2, pp. 14–15 | Campos conferidos nos CSVs locais',23,'#d8e8f4')
for x,title,body in [(40,'1. Validar','Elegibilidade + atividade efetiva'),(620,'2. Cruzar os dados','Empresa + unidade + bens + confiança'),(1200,'3. Confirmar','Exposição real e valores com o cliente')]:
 rect((x,180,x+550,290),'#e1edf8');tx(x+20,196,title,27,b=True);tx(x+20,244,body,21)
tx(593,218,'→',28,b=True);tx(1173,218,'→',28,b=True)
tx(58,311,'COBERTURA',18,b=True);tx(440,311,'SINAL DISPONÍVEL NOS DADOS',18,b=True);tx(1110,311,'O QUE PRECISA SER CONFIRMADO',18,b=True)
y=348
for group in dict.fromkeys(r['grupo'] for r in rows):
 items=[r for r in rows if r['grupo']==group]
 rect((40,y,1760,y+48),'#dcefeb');tx(58,y+9,group.upper(),23,'#24695c',True);y+=62
 for r in items:
  # Each row has the coverage, available evidence, and confirmation needed.
  h=max(len(textwrap.wrap(r['cobertura'],32))*27,len(textwrap.wrap(r['sinal'],67))*24,len(textwrap.wrap(r['confirmar'],64))*24)+22
  rect((40,y,1760,y+h),'white')
  lines(58,y+9,r['cobertura'],32,20,b=True)
  lines(440,y+9,r['sinal'],67,18)
  lines(1110,y+9,r['confirmar'],64,18)
  y+=h+7
 y+=12
# Crop to actual used height with a footer.
rect((40,y,1760,y+145),'#122e46');tx(60,y+14,'4. Comparar pacotes e opcionais compatíveis',28,'white',True)
lines(60,y+58,'Essencial + eletrônicos pode ser uma alternativa se as demais necessidades estiverem atendidas. Sem preço, não afirmar economia. Manter as seis obrigatórias; validar aceitação, limites e franquias.',139,21,'white')
end=y+172
if end>H:raise ValueError((end,H))
im=im.crop((0,0,W,end));im.save(out/'fluxograma-opcionais.png')
svg[0]=svg[0].replace(f'height="{H}"',f'height="{end}"').replace(f'0 0 {W} {H}',f'0 0 {W} {end}')
svg.append('</svg>');(out/'fluxograma-opcionais.svg').write_text('\n'.join(svg),encoding='utf-8')
print('Dimensões',W,end)
