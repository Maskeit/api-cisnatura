#!/bin/bash

# Script de inicio rápido para desarrollo con Stripe Webhooks

echo "🚀 Iniciando servicios de Cisnatura con Stripe..."
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar que Stripe CLI esté instalado
if ! command -v stripe &> /dev/null; then
    echo -e "${RED}❌ Stripe CLI no está instalado${NC}"
    echo "Instala Stripe CLI desde: https://stripe.com/docs/stripe-cli"
    exit 1
fi

echo -e "${GREEN}✅ Stripe CLI encontrado${NC}"
echo ""

# Verificar que Docker esté corriendo
if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker no está corriendo${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker está corriendo${NC}"
echo ""

# Instrucciones
echo -e "${YELLOW}📋 Instrucciones:${NC}"
echo ""
echo "1️⃣  En esta terminal se iniciará el webhook listener de Stripe"
echo "2️⃣  Abre otra terminal y ejecuta:"
echo "    cd api-cisnatura"
echo "    docker-compose logs app -f | grep -E 'Stripe|webhook|✅|❌|💰|🛒'"
echo ""
echo "3️⃣  Abre el frontend en: http://localhost:3000"
echo ""
echo -e "${GREEN}Presiona ENTER para continuar...${NC}"
read

# Iniciar Stripe listener
echo ""
echo -e "${GREEN}🔊 Iniciando Stripe webhook listener...${NC}"
echo ""
echo -e "${YELLOW}⚠️  IMPORTANTE: Deja esta terminal abierta${NC}"
echo ""

stripe listen --forward-to localhost:8000/payments/webhook/stripe
