# Obtener intereses de investigación de perfiles de Google Scholar
options(repos = c(CRAN = "https://cloud.r-project.org"))

if (!require("scholar")) install.packages("scholar")
library(scholar)

# DEBUG: Ver qué devuelve get_profile
message("=== DEBUG: Estructura del perfil ===")
test_profile <- get_profile("UknWOrEAAAAJ")
message("Tipo: ", class(test_profile))
message("Nombres de campos:")
print(names(test_profile))
message("\nContenido completo:")
print(test_profile)
message("=== FIN DEBUG ===\n")

# IDs y nombres de los investigadores
researchers <- data.frame(
  id = c(
    "oZGkFZoAAAAJ", "RdXwR1EAAAAJ", "e6FHWIMAAAAJ", "cV3jzO8AAAAJ",
    "IgwSc8oAAAAJ", "IBcs-ZwAAAAJ", "AP5zUGwAAAAJ", "pSjw4_gAAAAJ",
    "BPVbhToAAAAJ", "5q8wMVcAAAAJ", "gj1MwGwAAAAJ", "yyr6ge0AAAAJ",
    "dJKWN8wAAAAJ", "NcxMjkAAAAAJ", "8g7eKDcAAAAJ", "sHV_7OoAAAAJ",
    "DCQO_AgAAAAJ", "ckIjzZQAAAAJ", "gkHNPiwAAAAJ", "JD_X4KYAAAAJ",
    "NLiNCD0AAAAJ", "L8DtBnQAAAAJ", "k-2PLOsAAAAJ", "F7Dguu4AAAAJ",
    "6lYgX_0AAAAJ", "Y4q4OfoAAAAJ", "HaX6qs4AAAAJ", "UknWOrEAAAAJ"
  ),
  name = c(
    "David Altman", "Cristóbal Rovira Kaltwasser", "Manuel Antonio Garretón", "Lucia Dammert",
    "Juan Pablo Luna", "Patricio Navia", "Gabriel L. Negretto", "Peter Siavelis",
    "Mauricio Morales Quiroga", "Alfredo Joignant", "Carlos Huneeus", "Nicolás M. Somma",
    "Hugo Frühling", "Egon Montecinos", "Eugenio Tironi", "Kathya Araujo",
    "María Luisa Méndez", "Claudio Fuentes", "Rossana Castiglioni", "Carlos Meléndez",
    "Emmanuelle Barozet", "Vicente Espinoza", "Modesto Gayo", "Sergio Toro Maureira",
    "Jorge Atria", "Antoine Maillet", "Fernando Rosenblatt", "Bastián González-Bustamante"
  ),
  stringsAsFactors = FALSE
)

# Obtener intereses de todos
results <- list()

for (i in 1:nrow(researchers)) {
  id <- researchers$id[i]
  name <- researchers$name[i]

  message(sprintf("[%d/%d] %s...", i, nrow(researchers), name))

  tryCatch({
    profile <- get_profile(id)

    if (is.list(profile) && !is.null(profile$fields)) {
      interests <- paste(profile$fields, collapse = ", ")
      results[[id]] <- list(name = name, interests = interests)
      message(sprintf("  -> %s", interests))
    } else {
      results[[id]] <- list(name = name, interests = NA)
      message("  -> Sin intereses")
    }

    Sys.sleep(2)  # Pausa para evitar bloqueo

  }, error = function(e) {
    results[[id]] <<- list(name = name, interests = NA)
    message(sprintf("  -> Error: %s", e$message))
  })
}

# Crear dataframe con resultados
df <- do.call(rbind, lapply(names(results), function(id) {
  data.frame(
    scholar_id = id,
    nombre = results[[id]]$name,
    intereses = results[[id]]$interests,
    stringsAsFactors = FALSE
  )
}))

# Guardar CSV
write.csv(df, "g:/My Drive/ranking ciencias sociales/data/intereses_scholar.csv", row.names = FALSE)
message("\nResultados guardados en data/intereses_scholar.csv")
print(df)
