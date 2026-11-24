# Adjustment sets for one graph, computed with dagitty. Called by harness/dag.py.
#   Rscript harness/dagitty_sets.R <input.json> <output.json>
# Input:  {"edges": [["a","b"], ...], "exposure": "x", "outcome": "y", "unmeasured": ["u"]}
# Output: {"minimal": [[...], ...], "valid": [[...], ...]}
#   An empty inner list means "adjust for nothing". An empty outer list means no sufficient set exists.

suppressWarnings(suppressPackageStartupMessages({
  library(dagitty)
  library(jsonlite)
}))

args <- commandArgs(trailingOnly = TRUE)
spec <- fromJSON(args[1], simplifyVector = FALSE)

statements <- c(
  vapply(spec$unmeasured, function(u) sprintf("%s [latent]", u), character(1)),
  vapply(spec$edges, function(e) sprintf("%s -> %s", e[[1]], e[[2]]), character(1))
)
graph <- dagitty(sprintf("dag {\n%s\n}", paste(statements, collapse = "\n")))

sets_of <- function(type) {
  found <- adjustmentSets(graph, exposure = spec$exposure, outcome = spec$outcome,
                          type = type, effect = "total")
  unname(lapply(unclass(found), function(s) I(sort(as.character(s)))))
}

result <- list(minimal = sets_of("minimal"), valid = sets_of("all"))
writeLines(toJSON(result, auto_unbox = FALSE), args[2])
