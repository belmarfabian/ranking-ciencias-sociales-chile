# =============================================================================
# Ranking Chileno de Ciencias Sociales
# Script en R usando el paquete 'scholar'
# =============================================================================

# Configurar CRAN mirror
options(repos = c(CRAN = "https://cloud.r-project.org"))

# Instalar paquetes si no están instalados
if (!require("scholar")) install.packages("scholar")
if (!require("tidyverse")) install.packages("tidyverse")
if (!require("writexl")) install.packages("writexl")

library(scholar)
library(tidyverse)
library(writexl)

# -----------------------------------------------------------------------------
# Configuración
# -----------------------------------------------------------------------------

# Directorio de trabajo - AJUSTAR ESTA LÍNEA
setwd("G:/My Drive/ranking ciencias sociales")

# Archivo con IDs de investigadores
INPUT_FILE <- "data/seed/investigadores_chile.csv"

# Directorio de salida
OUTPUT_DIR <- "data/output"

# Delay entre requests (segundos) - MÁS ALTO = menos bloqueos
DELAY_SECONDS <- 5

# Reintentos máximos por autor
MAX_RETRIES <- 3

# -----------------------------------------------------------------------------
# Funciones
# -----------------------------------------------------------------------------

#' Obtiene datos de un autor con reintentos
#' @param scholar_id ID de Google Scholar
#' @param max_retries Número máximo de reintentos
#' @param delay_on_fail Segundos adicionales de espera si falla
#' @return data.frame con datos del autor o NULL si falla
get_author_data <- function(scholar_id, max_retries = 3, delay_on_fail = 10) {

  for (attempt in 1:max_retries) {
    result <- tryCatch({
      # Obtener perfil
      profile <- get_profile(scholar_id)

      # Verificar que tenemos datos válidos
      if (is.null(profile) || is.na(profile) || !is.list(profile)) {
        stop("Perfil vacío o inválido")
      }

      if (is.null(profile$name) || is.na(profile$name)) {
        stop("Nombre no disponible")
      }

      # Extraer datos
      data <- tibble(
        scholar_id = scholar_id,
        name = profile$name %||% NA,
        affiliation = profile$affiliation %||% NA,
        h_index = as.integer(profile$h_index %||% 0),
        i10_index = as.integer(profile$i10_index %||% 0),
        citations = as.integer(profile$total_cites %||% 0),
        fields = paste(profile$fields %||% "", collapse = "; "),
        homepage = profile$homepage %||% NA,
        extracted_at = Sys.time()
      )

      message(sprintf("OK %s (H:%d, C:%d)",
                      substr(profile$name, 1, 30),
                      data$h_index,
                      data$citations))

      return(data)

    }, error = function(e) {
      if (attempt < max_retries) {
        message(sprintf("  Intento %d fallido, reintentando en %ds...",
                        attempt, delay_on_fail))
        Sys.sleep(delay_on_fail)
      }
      return(NULL)
    })

    if (!is.null(result)) {
      return(result)
    }
  }

  message(sprintf("X Error con ID %s despues de %d intentos", scholar_id, max_retries))
  return(NULL)
}

# Operador null-coalescing para R
`%||%` <- function(x, y) if (is.null(x) || length(x) == 0 || all(is.na(x))) y else x

#' Procesa lista de IDs y obtiene datos
#' @param ids Vector de IDs de Google Scholar
#' @param delay Segundos de espera entre requests
#' @return data.frame con todos los autores
fetch_all_authors <- function(ids, delay = 5) {
  results <- list()
  n <- length(ids)
  failed <- character(0)

  message(sprintf("\nProcesando %d investigadores...\n", n))
  message(sprintf("Delay entre requests: %d segundos\n", delay))

  for (i in seq_along(ids)) {
    id <- trimws(ids[i])
    if (nchar(id) == 0) next

    message(sprintf("[%d/%d] %s: ", i, n, id), appendLF = FALSE)

    author_data <- get_author_data(id, max_retries = MAX_RETRIES)

    if (!is.null(author_data)) {
      results[[length(results) + 1]] <- author_data
    } else {
      failed <- c(failed, id)
    }

    # Delay para evitar bloqueos
    if (i < n) {
      Sys.sleep(delay)
    }
  }

  message(sprintf("\n\nExitosos: %d / %d", length(results), n))

  if (length(failed) > 0) {
    message(sprintf("Fallidos: %d", length(failed)))
    message("IDs fallidos: ", paste(failed, collapse = ", "))
  }

  # Combinar resultados
  if (length(results) > 0) {
    df <- bind_rows(results)
    return(df)
  } else {
    return(NULL)
  }
}

#' Genera el ranking ordenado
#' @param df data.frame con datos de autores
#' @return data.frame con ranking
generate_ranking <- function(df) {
  ranking <- df %>%
    arrange(desc(h_index), desc(citations)) %>%
    mutate(rank = row_number()) %>%
    select(rank, name, affiliation, h_index, citations, i10_index,
           fields, scholar_id, extracted_at)

  return(ranking)
}

#' Guarda resultados en múltiples formatos
#' @param ranking data.frame con ranking
#' @param output_dir Directorio de salida
save_results <- function(ranking, output_dir = "data/output") {
  # Crear directorio si no existe
  dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

  timestamp <- format(Sys.Date(), "%Y%m%d")
  base_name <- file.path(output_dir, paste0("ranking_ciencias_sociales_", timestamp))

  # CSV
  csv_file <- paste0(base_name, ".csv")
  write_csv(ranking, csv_file)
  message(sprintf("CSV guardado: %s", csv_file))

  # Excel
  xlsx_file <- paste0(base_name, ".xlsx")
  write_xlsx(ranking, xlsx_file)
  message(sprintf("Excel guardado: %s", xlsx_file))

  # Estadísticas
  stats <- tibble(
    Metrica = c("Total investigadores", "H-index promedio", "H-index mediana",
                "H-index maximo", "Citas totales", "Citas promedio"),
    Valor = c(nrow(ranking),
              round(mean(ranking$h_index, na.rm = TRUE), 2),
              median(ranking$h_index, na.rm = TRUE),
              max(ranking$h_index, na.rm = TRUE),
              sum(ranking$citations, na.rm = TRUE),
              round(mean(ranking$citations, na.rm = TRUE), 2))
  )

  stats_file <- paste0(base_name, "_stats.csv")
  write_csv(stats, stats_file)
  message(sprintf("Estadisticas: %s", stats_file))

  return(list(csv = csv_file, xlsx = xlsx_file, stats = stats_file))
}

# -----------------------------------------------------------------------------
# Ejecución Principal
# -----------------------------------------------------------------------------

main <- function() {
  message(strrep("=", 60))
  message("RANKING CHILENO DE CIENCIAS SOCIALES")
  message(strrep("=", 60))

  # Cargar IDs
  if (!file.exists(INPUT_FILE)) {
    stop(sprintf("No se encontro el archivo: %s", INPUT_FILE))
  }

  ids_df <- read_csv(INPUT_FILE, show_col_types = FALSE)
  ids <- ids_df$scholar_id

  message(sprintf("\nCargados %d IDs de investigadores", length(ids)))

  # Obtener datos
  authors <- fetch_all_authors(ids, delay = DELAY_SECONDS)

  if (is.null(authors) || nrow(authors) == 0) {
    stop("No se pudieron obtener datos. Google Scholar puede estar bloqueando.\n",
         "Intenta mas tarde o usa SerpAPI (ver README).")
  }

  message(sprintf("\n\nObtenidos datos de %d investigadores", nrow(authors)))

  # Generar ranking
  ranking <- generate_ranking(authors)

  # Guardar resultados
  message("\nGuardando resultados...")
  files <- save_results(ranking, OUTPUT_DIR)

  # Mostrar top 20
  message("\n", strrep("=", 60))
  message("TOP 20 INVESTIGADORES")
  message(strrep("=", 60))

  print(ranking %>%
          head(20) %>%
          select(rank, name, h_index, citations) %>%
          as.data.frame())

  message("\nProceso completado!")

  return(ranking)
}

# Ejecutar
# Si estás en RStudio, ejecuta: ranking <- main()
# Si ejecutas desde terminal: se ejecuta automáticamente
if (!interactive()) {
  ranking <- main()
} else {
  message("\nPara ejecutar, escribe: ranking <- main()")
}
