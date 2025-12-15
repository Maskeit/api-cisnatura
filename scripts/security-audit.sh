#!/bin/bash
# Script para ejecutar análisis de seguridad completo

set -e  # Detener si hay error

echo "════════════════════════════════════════════════════════════"
echo "         ANÁLISIS DE SEGURIDAD - CISNATURA API              "
echo "════════════════════════════════════════════════════════════"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 1. Bandit - Análisis estático
echo -e "\n${BLUE}1️⃣  Ejecutando Bandit (Análisis de Vulnerabilidades)...${NC}"
echo "════════════════════════════════════════════════════════════"
bandit -r /app -f json -o /app/scripts/bandit-report.json || true
bandit -r /app -f txt || true

# 2. pip-audit - Verificar dependencias vulnerables
echo -e "\n${BLUE}2️⃣  Ejecutando pip-audit (Dependencias)...${NC}"
echo "════════════════════════════════════════════════════════════"
pip-audit --format json > /app/scripts/pip-audit-report.json || true
pip-audit || true

# 3. Tests de seguridad
echo -e "\n${BLUE}3️⃣  Ejecutando Tests de Seguridad...${NC}"
echo "════════════════════════════════════════════════════════════"
if command -v pytest &> /dev/null; then
    if [ -f "/app/scripts/test_security.py" ]; then
        pytest /app/scripts/test_security.py -v --tb=short || true
    else
        echo -e "${YELLOW}⚠️  test_security.py no encontrado, saltando tests${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  pytest no instalado, saltando tests${NC}"
fi

# 4. Análisis de permisos en archivos
echo -e "\n${BLUE}4️⃣  Verificando Permisos de Archivos...${NC}"
echo "════════════════════════════════════════════════════════════"

# Verificar que no hay archivos ejecutables peligrosos
find /app -type f -executable | head -5 || echo "✅ Sin archivos ejecutables sospechosos"

# Verificar que no hay .env en git
if [ -f ".gitignore" ]; then
    if grep -q ".env" ".gitignore"; then
        echo "✅ .env está en .gitignore"
    else
        echo -e "${RED}❌ .env NO está en .gitignore${NC}"
    fi
fi

# 5. Búsqueda de strings peligrosos
echo -e "\n${BLUE}5️⃣  Buscando Patterns Peligrosos...${NC}"
echo "════════════════════════════════════════════════════════════"

dangerous_patterns=(
    "hardcoded.*password"
    "hardcoded.*secret"
    "api_key.*="
    "DISABLE_CSRF"
    "eval("
    "exec("
    "pickle"
)

found_issues=0

for pattern in "${dangerous_patterns[@]}"; do
    count=$(grep -r "$pattern" app/ 2>/dev/null | wc -l || echo 0)
    if [ $count -gt 0 ]; then
        echo -e "${RED}❌ Encontrado: $pattern ($count ocurrencias)${NC}"
        grep -r "$pattern" app/ 2>/dev/null | head -3
        found_issues=$((found_issues + 1))
    fi
done

if [ $found_issues -eq 0 ]; then
    echo -e "${GREEN}✅ No se encontraron patterns peligrosos${NC}"
fi

# 6. Resumen
echo -e "\n${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                    RESUMEN DEL ANÁLISIS                    ${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

echo -e "\n${GREEN}✅ Análisis completado.${NC}"
echo ""
echo "Archivos generados:"
echo "  - bandit-report.json (Reporte detallado de Bandit)"
echo "  - safety-report.json (Reporte de dependencias)"
echo ""
echo "Próximos pasos:"
echo "  1. Revisar bandit-report.json para vulnerabilidades"
echo "  2. Actualizar dependencias vulnerables: pip install --upgrade <package>"
echo "  3. Ejecutar tests: pytest tests/ -v"
echo "  4. Revisar seguridad de autenticación manualmente"
echo ""
echo "Documentación:"
echo "  - Bandit: https://bandit.readthedocs.io/"
echo "  - Safety: https://safety.readthedocs.io/"
echo "  - OWASP Top 10: https://owasp.org/www-project-top-ten/"
