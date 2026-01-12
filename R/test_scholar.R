# Test del paquete scholar - obtener intereses de investigación
options(repos = c(CRAN = "https://cloud.r-project.org"))

if (!require("scholar")) install.packages("scholar")
if (!require("httr")) install.packages("httr")
library(scholar)
library(httr)

# Configurar user agent para parecer navegador real
set_config(user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"))

message("=== Test del paquete scholar ===\n")

# Probar con un ID
test_id <- "UknWOrEAAAAJ"
message(sprintf("Probando ID: %s", test_id))

Sys.sleep(3)  # Esperar antes de la petición

tryCatch({
  profile <- get_profile(test_id)

  message("\nTipo de resultado: ", class(profile))

  if (is.list(profile)) {
    message("\nCampos disponibles:")
    print(names(profile))

    message("\n=== PERFIL ===")
    if (!is.null(profile$name)) message("Nombre: ", profile$name)
    if (!is.null(profile$affiliation)) message("Afiliación: ", profile$affiliation)
    if (!is.null(profile$total_cites)) message("Citas: ", profile$total_cites)
    if (!is.null(profile$h_index)) message("H-index: ", profile$h_index)

    # Buscar campos de intereses
    if (!is.null(profile$fields)) {
      message("\nIntereses (fields): ", paste(profile$fields, collapse = ", "))
    }
    if (!is.null(profile$interests)) {
      message("\nIntereses (interests): ", paste(profile$interests, collapse = ", "))
    }
    if (!is.null(profile$areas)) {
      message("\nÁreas (areas): ", paste(profile$areas, collapse = ", "))
    }

    message("\n=== Contenido completo ===")
    print(profile)

  } else {
    message("\nResultado no es lista. Valor: ", profile)
  }

}, error = function(e) {
  message("\nError: ", e$message)
})
