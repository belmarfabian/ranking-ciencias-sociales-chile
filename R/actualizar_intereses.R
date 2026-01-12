# =============================================================================
# ACTUALIZAR INTERESES DE INVESTIGACIÓN DESDE GOOGLE SCHOLAR
# =============================================================================
# Este script obtiene los intereses de investigación de los perfiles de
# Google Scholar y genera un archivo JSON para actualizar el HTML.
#
# USO: Ejecutar desde RStudio cuando Google Scholar no esté bloqueando
#      source("R/actualizar_intereses.R")
# =============================================================================

options(repos = c(CRAN = "https://cloud.r-project.org"))

# Instalar dependencias si no están
if (!require("scholar")) install.packages("scholar")
if (!require("jsonlite")) install.packages("jsonlite")
library(scholar)
library(jsonlite)

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

# Directorio base del proyecto
BASE_DIR <- "g:/My Drive/ranking ciencias sociales"

# Archivo de salida
OUTPUT_JSON <- file.path(BASE_DIR, "data/intereses_scholar.json")
OUTPUT_CSV <- file.path(BASE_DIR, "data/intereses_scholar.csv")

# Pausa entre peticiones (segundos) - aumentar si hay bloqueos
DELAY_SECONDS <- 3

# =============================================================================
# DATOS DE INVESTIGADORES
# =============================================================================

researchers <- data.frame(
  scholar_id = c(
    "oZGkFZoAAAAJ",
    "RdXwR1EAAAAJ",
    "e6FHWIMAAAAJ",
    "cV3jzO8AAAAJ",
    "IgwSc8oAAAAJ",
    "IBcs-ZwAAAAJ",
    "AP5zUGwAAAAJ",
    "pSjw4_gAAAAJ",
    "BPVbhToAAAAJ",
    "5q8wMVcAAAAJ",
    "gj1MwGwAAAAJ",
    "yyr6ge0AAAAJ",
    "dJKWN8wAAAAJ",
    "NcxMjkAAAAAJ",
    "8g7eKDcAAAAJ",
    "sHV_7OoAAAAJ",
    "DCQO_AgAAAAJ",
    "ckIjzZQAAAAJ",
    "gkHNPiwAAAAJ",
    "JD_X4KYAAAAJ",
    "NLiNCD0AAAAJ",
    "L8DtBnQAAAAJ",
    "k-2PLOsAAAAJ",
    "F7Dguu4AAAAJ",
    "6lYgX_0AAAAJ",
    "Y4q4OfoAAAAJ",
    "HaX6qs4AAAAJ",
    "UknWOrEAAAAJ"
  ),
  nombre = c(
    "David Altman",
    "Cristóbal Rovira Kaltwasser",
    "Manuel Antonio Garretón",
    "Lucia Dammert",
    "Juan Pablo Luna",
    "Patricio Navia",
    "Gabriel L. Negretto",
    "Peter Siavelis",
    "Mauricio Morales Quiroga",
    "Alfredo Joignant",
    "Carlos Huneeus",
    "Nicolás M. Somma",
    "Hugo Frühling",
    "Egon Montecinos",
    "Eugenio Tironi",
    "Kathya Araujo",
    "María Luisa Méndez",
    "Claudio Fuentes",
    "Rossana Castiglioni",
    "Carlos Meléndez",
    "Emmanuelle Barozet",
    "Vicente Espinoza",
    "Modesto Gayo",
    "Sergio Toro Maureira",
    "Jorge Atria",
    "Antoine Maillet",
    "Fernando Rosenblatt",
    "Bastián González-Bustamante"
  ),
  stringsAsFactors = FALSE
)

# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

obtener_intereses <- function(scholar_id, nombre) {
  tryCatch({
    profile <- get_profile(scholar_id)

    if (is.list(profile)) {
      # El paquete scholar usa "fields" para los intereses
      if (!is.null(profile$fields) && length(profile$fields) > 0) {
        return(paste(profile$fields, collapse = ", "))
      }
    }
    return(NA)
  }, error = function(e) {
    message(sprintf("  Error: %s", e$message))
    return(NA)
  })
}

# =============================================================================
# EJECUCIÓN
# =============================================================================

message("=" %>% rep(60) %>% paste(collapse = ""))
message("ACTUALIZACIÓN DE INTERESES DE INVESTIGACIÓN")
message("=" %>% rep(60) %>% paste(collapse = ""))
message(sprintf("Fecha: %s", Sys.time()))
message(sprintf("Total investigadores: %d", nrow(researchers)))
message(sprintf("Pausa entre peticiones: %d segundos", DELAY_SECONDS))
message("")

# Test inicial
message("Probando conexión con Google Scholar...")
test <- obtener_intereses("UknWOrEAAAAJ", "Test")
if (is.na(test)) {
  message("\n⚠️  ADVERTENCIA: Google Scholar parece estar bloqueando.")
  message("   Opciones:")
  message("   1. Esperar 30-60 minutos y volver a intentar")
  message("   2. Ejecutar desde una red diferente (VPN)")
  message("   3. Ejecutar desde RStudio (a veces funciona mejor)")
  message("\n¿Continuar de todas formas? (s/n)")

  # En modo no interactivo, continuar
  if (interactive()) {
    respuesta <- readline()
    if (tolower(respuesta) != "s") {
      message("Cancelado.")
      stop("Ejecución cancelada por el usuario")
    }
  }
}
message("")

# Obtener intereses de todos
results <- data.frame(
  scholar_id = character(),
  nombre = character(),
  intereses = character(),
  stringsAsFactors = FALSE
)

exitosos <- 0
fallidos <- 0

for (i in 1:nrow(researchers)) {
  id <- researchers$scholar_id[i]
  nombre <- researchers$nombre[i]

  message(sprintf("[%02d/%02d] %s", i, nrow(researchers), nombre))

  intereses <- obtener_intereses(id, nombre)

  if (!is.na(intereses)) {
    message(sprintf("        ✓ %s", intereses))
    exitosos <- exitosos + 1
  } else {
    message("        ✗ Sin datos")
    fallidos <- fallidos + 1
  }

  results <- rbind(results, data.frame(
    scholar_id = id,
    nombre = nombre,
    intereses = ifelse(is.na(intereses), "", intereses),
    stringsAsFactors = FALSE
  ))

  # Pausa entre peticiones (excepto en la última)
  if (i < nrow(researchers)) {
    Sys.sleep(DELAY_SECONDS)
  }
}

# =============================================================================
# GUARDAR RESULTADOS
# =============================================================================

message("")
message("-" %>% rep(60) %>% paste(collapse = ""))
message("RESULTADOS")
message("-" %>% rep(60) %>% paste(collapse = ""))
message(sprintf("Exitosos: %d", exitosos))
message(sprintf("Fallidos: %d", fallidos))

# Guardar CSV
write.csv(results, OUTPUT_CSV, row.names = FALSE, fileEncoding = "UTF-8")
message(sprintf("\nCSV guardado: %s", OUTPUT_CSV))

# Guardar JSON (para usar en JavaScript)
json_data <- toJSON(results, pretty = TRUE, auto_unbox = TRUE)
writeLines(json_data, OUTPUT_JSON, useBytes = TRUE)
message(sprintf("JSON guardado: %s", OUTPUT_JSON))

# =============================================================================
# GENERAR CÓDIGO PARA ACTUALIZAR HTML
# =============================================================================

message("")
message("=" %>% rep(60) %>% paste(collapse = ""))
message("CÓDIGO PARA ACTUALIZAR HTML")
message("=" %>% rep(60) %>% paste(collapse = ""))
message("")
message("Copia este objeto JavaScript y reemplázalo en index.html:")
message("")

# Generar mapa de intereses
intereses_con_datos <- results[results$intereses != "", ]
if (nrow(intereses_con_datos) > 0) {
  message("const topicsFromScholar = {")
  for (j in 1:nrow(intereses_con_datos)) {
    coma <- ifelse(j < nrow(intereses_con_datos), ",", "")
    message(sprintf('  "%s": "%s"%s  // %s',
                    intereses_con_datos$scholar_id[j],
                    intereses_con_datos$intereses[j],
                    coma,
                    intereses_con_datos$nombre[j]))
  }
  message("};")
} else {
  message("// No se obtuvieron intereses - Google Scholar bloqueó las peticiones")
}

message("")
message("=" %>% rep(60) %>% paste(collapse = ""))
message("FIN")
message("=" %>% rep(60) %>% paste(collapse = ""))
