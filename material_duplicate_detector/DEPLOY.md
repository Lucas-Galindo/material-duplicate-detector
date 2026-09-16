# Deploy da versao Web na VM (Oracle Cloud / Ubuntu)

Este guia assume uma instancia Ubuntu com Nginx ja instalado (mesmo
padrao usado nas atividades anteriores com Node.js), so que agora o
Nginx faz proxy reverso para uma aplicacao **Python + Flask + Gunicorn**
em vez de Node.js. A porta interna da aplicacao e a **3000**, igual ao
exemplo do professor.

## 1. Enviar o projeto para a VM

Use o FileZilla (SFTP, porta 22, usuario `ubuntu`, sua chave `.key`)
para copiar a pasta `material_duplicate_detector` inteira para
`/home/ubuntu/material_duplicate_detector` na VM. Ou, se preferir,
compacte e envie so o `.zip` e descompacte la:

```bash
cd /home/ubuntu
unzip material_duplicate_detector.zip
cd material_duplicate_detector
```

## 2. Instalar Python, criar o ambiente virtual e as dependencias

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip

cd /home/ubuntu/material_duplicate_detector
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> Se so quiser as dependencias da web (sem PyInstaller, que e so para
> gerar o `.exe` desktop), pode instalar so o necessario:
> `pip install pandas openpyxl flask gunicorn`

## 3. Testar rapido antes de virar servico

```bash
source venv/bin/activate
gunicorn -w 2 -b 0.0.0.0:3000 "app.web:app"
```

Em outra sessao SSH (ou do seu navegador, se a porta 3000 estiver
liberada temporariamente), teste:

```bash
curl localhost:3000/healthz
# esperado: {"status":"ok"}
```

Se aparecer o JSON acima, a aplicacao esta rodando. Pare com `Ctrl+C`
antes de seguir para o proximo passo (o servico systemd vai assumir a
partir daqui).

## 4. Criar o servico systemd (mantem a aplicacao sempre no ar)

```bash
sudo nano /etc/systemd/system/appdemo1.service
```

Cole:

```ini
[Unit]
Description=Detector de Duplicidade de Materiais (Flask/Gunicorn)
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/material_duplicate_detector
Environment="PATH=/home/ubuntu/material_duplicate_detector/venv/bin"
ExecStart=/home/ubuntu/material_duplicate_detector/venv/bin/gunicorn -w 2 -b 127.0.0.1:3000 app.web:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Registrar, iniciar e conferir o status:

```bash
sudo systemctl daemon-reload
sudo systemctl enable appdemo1.service
sudo systemctl start appdemo1.service
sudo systemctl status appdemo1.service
```

## 5. Configurar o Nginx como proxy reverso

```bash
sudo nano /etc/nginx/sites-available/default
```

Dentro do bloco `server { ... }`, na secao `location / { ... }`, use:

```nginx
location / {
    proxy_pass http://localhost:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    client_max_body_size 50M;  # precisa ser >= MAX_CONTENT_LENGTH do Flask (50 MB)
}
```

Testar a sintaxe e recarregar:

```bash
sudo nginx -t
sudo systemctl restart nginx
```

## 6. Liberar a porta 80 (se ainda nao estiver liberada)

Ja deve estar liberada das atividades anteriores, mas por garantia:

- **Security List da sub-rede (OCI):** regra de entrada TCP porta 80, origem `0.0.0.0/0`.
- **IPTABLES da instancia:**
  ```bash
  sudo iptables -I INPUT 1 -p tcp --dport 80 -j ACCEPT
  sudo netfilter-persistent save
  sudo netfilter-persistent reload
  ```
  (usar `-I INPUT 1`, nao `-A`, para garantir que a regra fica antes de
  qualquer REJECT ja existente na cadeia — ver observacao abaixo.)

> **Atencao:** em VMs Ubuntu da Oracle Cloud, a cadeia `INPUT` do
> iptables costuma ja ter uma regra `REJECT` no meio. Se voce usar
> `-A` (append), sua regra nova cai *depois* do REJECT e nunca funciona.
> Sempre confira com `sudo iptables -L INPUT -n --line-numbers` antes,
> e use `-I INPUT 1` para inserir no topo se houver duvida.

## 7. Testar

Abra o navegador em `http://<IP_PUBLICO_DA_VM>` — deve aparecer a tela
de upload da aplicacao (nao mais a pagina padrao do Nginx).

## Comandos uteis

```bash
# ver logs do servico em tempo real
sudo journalctl -u appdemo1.service -f

# reiniciar apos alterar codigo
sudo systemctl restart appdemo1.service

# parar/iniciar
sudo systemctl stop appdemo1.service
sudo systemctl start appdemo1.service
```
