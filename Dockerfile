# Usar Python 3.12 slim-bookworm como base
FROM python:3.12-slim-bookworm

# Establecer el directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para psycopg2
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de dependencias desde la raíz (al directorio padre)
WORKDIR /
COPY requirements.txt requirements-dev.txt ./

# Instalar las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Argument para instalar dev tools (por defecto false)
ARG INSTALL_DEV=false
RUN if [ "$INSTALL_DEV" = "true" ] ; then pip install --no-cache-dir -r requirements-dev.txt ; fi

# Volver al directorio de trabajo
WORKDIR /app

# Copiar la aplicación
COPY ./app .

# Exponer el puerto 8000
EXPOSE 8000

# Comando por defecto (se puede sobrescribir en docker-compose)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
