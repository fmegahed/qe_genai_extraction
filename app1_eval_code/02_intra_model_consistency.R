# This file performs the following steps:
# 1. Load all model extraction results from the results/ folder.
# 2. Compute the modal (largest) group of identical values per model,
#    document, and field, treating NA / empty values as disagreements.
# 3. Assemble per-model, per-document exact-match counts (intra-model consistency).
# 4. Summarize consistency at the model level.
# 5. Save both tables to CSV files in the results/ folder.


# 1. Load all model extraction results from the results/ folder
result_files = list.files(
  path = "results/",
  pattern = "^recalls_extracted_.*\\.csv$",
  full.names = TRUE
)

all_results = purrr::map_dfr(
  result_files,
  function(file) {
    readr::read_csv(
      file,
      col_types = readr::cols(
        document_id = readr::col_integer(),
        model_name = readr::col_character(),
        repeat_id = readr::col_integer(),
        temperature = readr::col_double(),
        manufacturer = readr::col_character(),
        models = readr::col_character(),
        model_years = readr::col_character(),
        success = readr::col_logical(),
        error_message = readr::col_character(),
        runtime_sec = readr::col_double(),
        chat_timestamp = readr::col_datetime(format = "")
      )
    )
  }
)

# Build one combined string representing the full extraction.
# If any field is missing, the full extraction is treated as missing.
all_results = all_results |>
  dplyr::mutate(
    full_extraction = dplyr::if_else(
      is.na(manufacturer) | is.na(models) | is.na(model_years),
      NA_character_,
      paste(
        manufacturer,
        models,
        model_years,
        sep = " || "
      )
    )
  )


# 2. Compute the modal group size per model, document, and field.
# Reshape to long format so all fields are handled by one rule:
# NA / empty values always count as disagreements, so they are filtered out
# before counting and can never form an agreeing group. For example, four NAs
# and one value give a count of 1; five NAs give a count of 0 (such groups
# drop out here and are restored with a 0 in step 3).
fields = c("manufacturer", "models", "model_years", "full_extraction")

modal_counts = all_results |>
  tidyr::pivot_longer(
    cols = dplyr::all_of(fields),
    names_to = "field",
    values_to = "value"
  ) |>
  dplyr::filter(
    !is.na(value),
    trimws(value) != ""
  ) |>
  dplyr::count(model_name, document_id, field, value) |>
  dplyr::slice_max(
    n,
    n = 1,
    with_ties = FALSE,
    by = c(model_name, document_id, field)
  ) |>
  dplyr::select(model_name, document_id, field, n_matching = n)


# 3. Assemble per-model, per-document exact-match counts.
# A field is flagged consistent when every repeat returned the exact same
# non-missing value.
consistency_by_document = all_results |>
  dplyr::summarise(
    n_repeats = dplyr::n(),
    n_success = sum(success, na.rm = TRUE),
    .by = c(model_name, document_id)
  ) |>
  tidyr::crossing(field = fields) |>
  dplyr::left_join(
    modal_counts,
    by = c("model_name", "document_id", "field")
  ) |>
  dplyr::mutate(
    n_matching = tidyr::replace_na(n_matching, 0L),
    consistent = n_matching == n_repeats
  ) |>
  tidyr::pivot_wider(
    names_from = field,
    values_from = c(n_matching, consistent),
    names_glue = "{field}_{.value}"
  ) |>
  dplyr::rename(fully_consistent = full_extraction_consistent) |>
  dplyr::arrange(model_name, document_id)


# 4. Summarize consistency at the model level.
consistency_by_model = consistency_by_document |>
  dplyr::summarise(
    n_documents = dplyr::n(),
    n_extractions = sum(n_repeats),
    n_success = sum(n_success),
    n_manufacturer_consistent_docs = sum(manufacturer_consistent),
    n_models_consistent_docs = sum(models_consistent),
    n_model_years_consistent_docs = sum(model_years_consistent),
    n_fully_consistent_docs = sum(fully_consistent),
    prop_fully_consistent_docs = mean(fully_consistent),
    mean_full_extraction_n_matching = mean(full_extraction_n_matching),
    .by = model_name
  ) |>
  dplyr::arrange(
    dplyr::desc(prop_fully_consistent_docs)
  )


# 5. Save both tables to CSV files in the results/ folder.
readr::write_csv(
  consistency_by_document,
  "results/consistency_by_document.csv",
  na = ""
)

readr::write_csv(
  consistency_by_model,
  "results/consistency_by_model.csv",
  na = ""
)

print(consistency_by_model)
