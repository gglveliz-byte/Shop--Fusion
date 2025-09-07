<?php
session_start();
if (!isset($_SESSION['logueado']) || $_SESSION['logueado'] !== true) {
    header("Location: admin.php");
    exit();
}

$json_file = 'productos.json';

// Editar producto
if (isset($_GET['editar'])) {
    $editar_index = (int)$_GET['editar'];
    if (file_exists($json_file)) {
        $productos = json_decode(file_get_contents($json_file), true);
        if (isset($productos[$editar_index])) {
            $edit_product = $productos[$editar_index];
        }
    }
}

// Eliminar producto
if (isset($_GET['eliminar'])) {
    $index = (int)$_GET['eliminar'];
    if (file_exists($json_file)) {
        $productos = json_decode(file_get_contents($json_file), true);
        if (isset($productos[$index])) {
            array_splice($productos, $index, 1);
            file_put_contents($json_file, json_encode($productos, JSON_PRETTY_PRINT));
            $mensaje = "✅ Producto eliminado correctamente";
        }
    }
}

// Agregar o actualizar producto
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $nombre = htmlspecialchars($_POST['nombre']);
    $afiliacion = htmlspecialchars($_POST['afiliacion']);
    $descripcion = htmlspecialchars($_POST['descripcion']);
    $link = htmlspecialchars($_POST['link']);

    // Manejo de media opcional
    $media = [];
    for ($i = 1; $i <= 5; $i++) {
        $key = 'media'.$i;
        if (!empty($_POST[$key])) {
            $urls = array_filter(array_map('trim', explode(',', $_POST[$key])));
            $media = array_merge($media, $urls);
        }
    }

    $productos = file_exists($json_file) ? json_decode(file_get_contents($json_file), true) : [];

    if (isset($_POST['index']) && $_POST['index'] !== '') {
        // Actualizar producto existente
        $productos[(int)$_POST['index']] = [
            'nombre' => $nombre,
            'afiliacion' => $afiliacion,
            'descripcion' => $descripcion,
            'media' => $media,
            'link' => $link
        ];
        $mensaje = "✅ Producto actualizado correctamente";
    } else {
        // Agregar nuevo producto
        $productos[] = [
            'nombre' => $nombre,
            'afiliacion' => $afiliacion,
            'descripcion' => $descripcion,
            'media' => $media,
            'link' => $link
        ];
        $mensaje = "✅ Producto agregado correctamente";
    }

    file_put_contents($json_file, json_encode($productos, JSON_PRETTY_PRINT));
}

// Leer productos existentes para mostrar
$productos = file_exists($json_file) ? json_decode(file_get_contents($json_file), true) : [];
?>

<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Panel Admin</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; background: #f0f0f0; }
        h2, h3 { color: #333; }
        form { background: #fff; padding: 20px; border-radius: 8px; max-width: 600px; margin-bottom: 30px; }
        input, select, textarea, button { width: 100%; margin-bottom: 15px; padding: 8px; border-radius: 4px; border: 1px solid #ccc; }
        button { background: #1976d2; color: #fff; border: none; cursor: pointer; }
        button:hover { background: #1565c0; }
        .mensaje { color: green; font-weight: bold; }
        .productos-list { background: #fff; padding: 20px; border-radius: 8px; max-width: 800px; }
        .producto-item { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; border-bottom: 1px solid #ccc; padding-bottom: 5px; }
        .producto-item button { margin-left: 10px; }
        .btn-eliminar { background: #e53935; color: #fff; border: none; padding: 5px 10px; cursor: pointer; }
        .btn-eliminar:hover { background: #c62828; }
        .btn-editar { background: #fbc02d; color: #fff; border: none; padding: 5px 10px; cursor: pointer; }
        .btn-editar:hover { background: #f9a825; }
    </style>
</head>
<body>
    <h2>Panel de Administración</h2>
    <?php if (isset($mensaje)) echo "<p class='mensaje'>$mensaje</p>"; ?>

    <form method="post">
        <input type="hidden" name="index" value="<?php echo isset($edit_product) ? $editar_index : ''; ?>">

        <label>Nombre del producto:</label>
        <input type="text" name="nombre" required value="<?php echo isset($edit_product) ? htmlspecialchars($edit_product['nombre']) : ''; ?>">

        <label>Afiliación:</label>
        <select name="afiliacion" required>
            <?php
            $afiliaciones = ["Amazon Associates","Rakuten Advertising","Awin","ClickBank","Digistore24"];
            foreach ($afiliaciones as $af) {
                $selected = (isset($edit_product) && $edit_product['afiliacion']==$af) ? 'selected' : '';
                echo "<option value='$af' $selected>$af</option>";
            }
            ?>
        </select>

        <label>Descripción:</label>
        <textarea name="descripcion" rows="4" required><?php echo isset($edit_product) ? htmlspecialchars($edit_product['descripcion']) : ''; ?></textarea>

        <label>Link de afiliado:</label>
        <input type="text" name="link" required value="<?php echo isset($edit_product) ? htmlspecialchars($edit_product['link']) : ''; ?>">

        <!-- Campos de medios separados -->
        <?php
        for ($i=1; $i<=5; $i++) {
            $value = '';
            if (isset($edit_product) && isset($edit_product['media'][$i-1])) {
                $value = htmlspecialchars($edit_product['media'][$i-1]);
            }
            echo "<label>Media $i (opcional, URLs separadas por coma):</label>";
            echo "<textarea name='media$i' placeholder='https://url1.jpg, https://url2.mp4'>$value</textarea>";
        }
        ?>

        <button type="submit"><?php echo isset($edit_product) ? 'Actualizar producto' : 'Agregar producto'; ?></button>
    </form>

    <div class="productos-list">
        <h3>Productos existentes</h3>
        <?php if(!empty($productos)): ?>
            <?php foreach($productos as $i => $prod): ?>
                <div class="producto-item">
                    <span><?php echo htmlspecialchars($prod['nombre']); ?></span>
                    <div>
                        <a href="?editar=<?php echo $i; ?>"><button class="btn-editar">Editar</button></a>
                        <a href="?eliminar=<?php echo $i; ?>" onclick="return confirm('¿Eliminar este producto?');"><button class="btn-eliminar">Eliminar</button></a>
                    </div>
                </div>
            <?php endforeach; ?>
        <?php else: ?>
            <p>No hay productos agregados.</p>
        <?php endif; ?>
    </div>

    <br>
    <a href="productos.json" target="_blank">Ver productos agregados</a>
</body>
</html>
