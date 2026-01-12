# Scraping directo de intereses de Google Scholar
options(repos = c(CRAN = "https://cloud.r-project.org"))

if (!require("rvest")) install.packages("rvest")
if (!require("httr")) install.packages("httr")
library(rvest)
library(httr)

get_scholar_interests <- function(scholar_id) {
  url <- sprintf("https://scholar.google.com/citations?user=%s&hl=en", scholar_id)

  # Simular navegador
  response <- GET(
    url,
    add_headers(
      "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      "Accept" = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language" = "en-US,en;q=0.5"
    )
  )

  if (status_code(response) != 200) {
    return(list(success = FALSE, error = sprintf("HTTP %d", status_code(response))))
  }

  page <- read_html(content(response, "text", encoding = "UTF-8"))

  # Buscar intereses - están en links con class "gsc_prf_inta"
  interests <- page %>%
    html_nodes(".gsc_prf_inta") %>%
    html_text()

  # También buscar el nombre
  name <- page %>%
    html_node("#gsc_prf_in") %>%
    html_text()

  if (length(interests) == 0) {
    # Verificar si hay CAPTCHA
    captcha <- page %>% html_node("#captcha") %>% html_text()
    if (!is.na(captcha)) {
      return(list(success = FALSE, error = "CAPTCHA detectado"))
    }
    return(list(success = TRUE, name = name, interests = character(0)))
  }

  return(list(success = TRUE, name = name, interests = interests))
}

# Test
message("=== Scraping directo de Google Scholar ===\n")

test_id <- "UknWOrEAAAAJ"
message(sprintf("Probando ID: %s\n", test_id))

Sys.sleep(2)
result <- get_scholar_interests(test_id)

if (result$success) {
  message("Nombre: ", result$name)
  if (length(result$interests) > 0) {
    message("Intereses: ", paste(result$interests, collapse = ", "))
  } else {
    message("No se encontraron intereses (puede estar bloqueado)")
  }
} else {
  message("Error: ", result$error)
}
