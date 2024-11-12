# Usar uma imagem oficial do Python como base
FROM python:3.12.2-alpine

# Definir o diretório de trabalho no contêiner
WORKDIR /app

RUN mkdir uploads

# Copiar o arquivo de dependências para o contêiner
COPY requirements.txt ./

RUN pip install --upgrade pip

# Instalar as dependências
RUN pip install -r requirements.txt

# Copiar o restante do código da aplicação para o contêiner
COPY . .

# Expor a porta que o render.com irá utilizar
EXPOSE 10000

# Comando para iniciar a aplicação usando gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "index:app"]
