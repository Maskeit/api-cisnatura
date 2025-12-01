# Resumen de Endpoints GET - Admin Settings

## 🎯 Nuevos Endpoints GET Específicos

Ahora cada panel en tu frontend puede obtener **solo la información que necesita**.

### 📍 Endpoints Disponibles

| Endpoint | Descripción | Uso en Frontend |
|----------|-------------|-----------------|
| `GET /admin/settings` | **TODO** el objeto de configuraciones | Dashboard principal |
| `GET /admin/settings/maintenance` | Solo modo mantenimiento | Panel de Mantenimiento |
| `GET /admin/settings/shipping` | Solo configuración de envío | Panel de Envío |
| `GET /admin/settings/discounts` | Todos los descuentos (global + categorías + productos) | Panel de Descuentos (vista general) |
| `GET /admin/settings/discount/global` | Solo descuento global | Sección de descuento global |
| `GET /admin/settings/discount/categories` | Solo descuentos por categoría | Tabla de descuentos por categoría |
| `GET /admin/settings/discount/products` | Solo descuentos por producto | Tabla de descuentos por producto |
| `GET /admin/settings/seasonal-offers` | Solo ofertas temporales | Panel de Ofertas Estacionales |
| `GET /admin/settings/registration` | Registro + max items | Panel de Configuración General |

---

## 💡 Casos de Uso

### Caso 1: Panel de Descuentos con Tabs

```jsx
const DiscountsPanel = () => {
  const [activeTab, setActiveTab] = useState('all');
  const [data, setData] = useState(null);

  const loadData = async () => {
    let endpoint = '/admin/settings/discounts'; // Por defecto todos
    
    if (activeTab === 'global') endpoint = '/admin/settings/discount/global';
    if (activeTab === 'categories') endpoint = '/admin/settings/discount/categories';
    if (activeTab === 'products') endpoint = '/admin/settings/discount/products';
    
    const res = await fetch(endpoint, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const json = await res.json();
    setData(json.data);
  };

  return (
    <div>
      <Tabs onChange={setActiveTab}>
        <Tab value="all">Todos</Tab>
        <Tab value="global">Global</Tab>
        <Tab value="categories">Categorías</Tab>
        <Tab value="products">Productos</Tab>
      </Tabs>
      
      {/* Renderiza según activeTab */}
    </div>
  );
};
```

### Caso 2: Cargar solo lo necesario al abrir cada panel

```jsx
// MainDashboard.jsx
const MainDashboard = () => {
  return (
    <div className="dashboard">
      {/* Cada panel carga su propia información */}
      <MaintenancePanel />  {/* GET /admin/settings/maintenance */}
      <ShippingPanel />     {/* GET /admin/settings/shipping */}
      <DiscountsPanel />    {/* GET /admin/settings/discounts */}
    </div>
  );
};
```

### Caso 3: Actualizar solo una sección después de cambios

```jsx
const deleteProductDiscount = async (productId) => {
  // 1. Eliminar
  await fetch(`/admin/settings/discount/product/${productId}`, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  // 2. Recargar SOLO descuentos de productos (no todo el settings)
  const res = await fetch('/admin/settings/discount/products', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const data = await res.json();
  
  // 3. Actualizar estado local
  setProductDiscounts(data.data.product_discounts);
};
```

---

## 📊 Comparación: Antes vs Ahora

### ❌ ANTES (Ineficiente)

```jsx
// Todos los paneles pedían TODO el objeto
const MaintenancePanel = () => {
  useEffect(() => {
    fetch('/admin/settings') // 🔴 Trae TODO
      .then(res => res.json())
      .then(data => {
        // Solo usa maintenance_mode y maintenance_message
        setMaintenance(data.maintenance_mode);
        setMessage(data.maintenance_message);
      });
  }, []);
};

// Respuesta: 500+ líneas con todo el JSON
```

### ✅ AHORA (Eficiente)

```jsx
// Cada panel pide solo lo que necesita
const MaintenancePanel = () => {
  useEffect(() => {
    fetch('/admin/settings/maintenance') // ✅ Solo mantenimiento
      .then(res => res.json())
      .then(data => {
        setMaintenance(data.data.maintenance_mode);
        setMessage(data.data.maintenance_message);
      });
  }, []);
};

// Respuesta: Solo 4 líneas relevantes
{
  "success": true,
  "status_code": 200,
  "message": "Configuración de mantenimiento obtenida exitosamente",
  "data": {
    "maintenance_mode": false,
    "maintenance_message": "Sistema en mantenimiento..."
  }
}
```

---

## 🔄 Flujo Completo: Gestionar Descuentos por Producto

```jsx
// 1. Cargar lista de productos con descuentos
const loadProductDiscounts = async () => {
  const res = await fetch('/admin/settings/discount/products', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const data = await res.json();
  
  // Respuesta:
  // {
  //   "data": {
  //     "product_discounts": {
  //       "1": { "percentage": 20, "name": "Liquidación" },
  //       "5": { "percentage": 15, "name": "Oferta" }
  //     }
  //   }
  // }
  
  setDiscounts(data.data.product_discounts);
};

// 2. Agregar nuevo descuento
const addDiscount = async (productId, percentage, name) => {
  await fetch('/admin/settings/discount/product', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      product_id: productId,
      percentage: percentage,
      name: name
    })
  });
  
  // 3. Recargar lista actualizada
  await loadProductDiscounts();
};

// 4. Eliminar descuento
const deleteDiscount = async (productId) => {
  await fetch(`/admin/settings/discount/product/${productId}`, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  // 5. Recargar lista actualizada
  await loadProductDiscounts();
};
```

---

## 🎨 Ejemplo de UI: Lista de Descuentos

```jsx
const ProductDiscountsList = () => {
  const [discounts, setDiscounts] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/admin/settings/discount/products', {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    })
      .then(res => res.json())
      .then(data => {
        setDiscounts(data.data.product_discounts);
        setLoading(false);
      });
  }, []);

  const handleDelete = async (productId) => {
    if (!confirm('¿Eliminar este descuento?')) return;
    
    await fetch(`/admin/settings/discount/product/${productId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    });
    
    // Recargar
    const res = await fetch('/admin/settings/discount/products', {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    });
    const data = await res.json();
    setDiscounts(data.data.product_discounts);
  };

  if (loading) return <Spinner />;

  return (
    <table className="discounts-table">
      <thead>
        <tr>
          <th>Producto ID</th>
          <th>Nombre Oferta</th>
          <th>Descuento</th>
          <th>Acciones</th>
        </tr>
      </thead>
      <tbody>
        {Object.entries(discounts).length === 0 ? (
          <tr>
            <td colSpan="4">No hay descuentos por producto</td>
          </tr>
        ) : (
          Object.entries(discounts).map(([productId, disc]) => (
            <tr key={productId}>
              <td>{productId}</td>
              <td>{disc.name}</td>
              <td>{disc.percentage}%</td>
              <td>
                <button 
                  onClick={() => handleDelete(productId)}
                  className="btn-delete"
                >
                  🗑️ Eliminar
                </button>
              </td>
            </tr>
          ))
        )}
      </tbody>
    </table>
  );
};
```

---

## ✅ Ventajas de esta Arquitectura

1. **Performance**: Menos datos transferidos en cada request
2. **Simplicidad**: Cada componente solo maneja lo que necesita
3. **Escalabilidad**: Fácil agregar nuevos paneles sin afectar otros
4. **Cache**: Puedes cachear cada endpoint independientemente
5. **Testing**: Más fácil hacer tests unitarios de cada panel
6. **UX**: Los paneles cargan más rápido (menos datos)

---

## 🚀 Próximos Pasos

1. **Actualizar tu frontend** para usar los nuevos endpoints GET específicos
2. **Eliminar** llamadas a `/admin/settings` completo donde no sea necesario
3. **Implementar** paneles independientes con lazy loading
4. **Cachear** respuestas específicas (ej: configuración de envío cambia poco)
5. **Agregar** loading states y error handling por panel

---

## 📝 Checklist de Migración

- [ ] Panel de Mantenimiento → `GET /admin/settings/maintenance`
- [ ] Panel de Envío → `GET /admin/settings/shipping`
- [ ] Panel de Descuentos (vista general) → `GET /admin/settings/discounts`
- [ ] Descuento Global → `GET /admin/settings/discount/global`
- [ ] Lista de Categorías con descuento → `GET /admin/settings/discount/categories`
- [ ] Lista de Productos con descuento → `GET /admin/settings/discount/products`
- [ ] Ofertas Temporales → `GET /admin/settings/seasonal-offers`
- [ ] Configuración de Registro → `GET /admin/settings/registration`

---

**Documentación completa:** `docs/ADMIN-SETTINGS.md`
