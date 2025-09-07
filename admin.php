<?php
session_start();

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $usuario = $_POST['usuario'];
    $password = $_POST['password'];

    // Credenciales provisionales
    $user = "lveliz213";
    $pass = "admin";

    if ($usuario === $user && $password === $pass) {
        $_SESSION['logueado'] = true;
        header("Location: panel.php");
        exit();
    } else {
        $error = "Usuario o contraseña incorrectos";
    }
}
?>

<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Login Admin</title>
</head>
<body>
  <h2>Acceso Administrador</h2>
  <?php if (isset($error)) echo "<p style='color:red;'>$error</p>"; ?>
  <form method="post">
    <label>Usuario:</label>
    <input type="text" name="usuario" required><br><br>
    <label>Contraseña:</label>
    <input type="password" name="password" required><br><br>
    <button type="submit">Ingresar</button>
  </form>
</body>
</html>
