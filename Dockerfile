# Usar uma imagem oficial do Python como base
FROM python:3.9-slim

# Definir o diretório de trabalho no contêiner
WORKDIR /app

# Copiar o arquivo de dependências para o contêiner
COPY requirements.txt ./

# Instalar as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código da aplicação para o contêiner
COPY . .

# Expor a porta que o render.com irá utilizar
EXPOSE 10000

# Comando para iniciar a aplicação usando gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "index:app"]
