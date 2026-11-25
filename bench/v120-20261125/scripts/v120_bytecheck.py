#!/usr/bin/env python3
import hashlib,json,pathlib,sys,urllib.request

out=pathlib.Path(sys.argv[1])
key=pathlib.Path('/home/plogan/.config/llm-gateway/api-key').read_text().strip()

def post(body):
    req=urllib.request.Request('http://127.0.0.1:5806/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+key})
    with urllib.request.urlopen(req,timeout=900) as r:
        return json.loads(r.read())

def long_prompt():
    rows=[]
    for i in range(3800):
        rows.append(f'archive row {i}: station {chr(65+i%26)}{(i*17)%100} reports pressure {(i*37)%991} temperature {(i*29)%83} checksum {(i*11)%313} with stable telemetry and ordinary operational notes.')
    return 'The archive codeword is ZEBRA-417.\n' + '\n'.join(rows) + '\nQuestion: what is the archive codeword? Answer with only the codeword.'

cases=[
    {'id':'short-code','prompt':'Write a Python function that returns the nth Fibonacci number. Include only code.','max_tokens':160},
    {'id':'long-archive','prompt':long_prompt(),'max_tokens':96},
]
results=[]
for c in cases:
    body={'model':'local-ai','messages':[{'role':'user','content':c['prompt']}], 'temperature':0,'max_tokens':c['max_tokens'],'chat_template_kwargs':{'enable_thinking':False}}
    r=post(body)
    ch=r['choices'][0]
    msg=ch.get('message',{})
    item={'id':c['id'],'content':msg.get('content') or '', 'reasoning':msg.get('reasoning_content') or '', 'finish_reason':ch.get('finish_reason'), 'completion_tokens':r.get('usage',{}).get('completion_tokens'), 'prompt_tokens':r.get('usage',{}).get('prompt_tokens')}
    blob=(item['content']+'\0'+item['reasoning']).encode()
    item['sha256']=hashlib.sha256(blob).hexdigest()
    results.append(item)
out.write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
