import secrets  
  
key = secrets.token_urlsafe(32)  
print(f'Generated JWT_SECRET_KEY: {key}')  
  
with open('.env', 'r') as f:  
    content = f.read()  
  
if 'JWT_SECRET_KEY' in content:  
    lines = content.split('\n')  
    new_lines = []  
    for line in lines:  
        if line.startswith('JWT_SECRET_KEY='):  
            new_lines.append(f'JWT_SECRET_KEY={key}')  
        else:  
            new_lines.append(line)  
    content = '\n'.join(new_lines)  
else:  
    content = content.rstrip() + f'\nJWT_SECRET_KEY={key}\n'  
  
with open('.env', 'w') as f:  
    f.write(content)  
  
print('JWT_SECRET_KEY saved to .env file') 
