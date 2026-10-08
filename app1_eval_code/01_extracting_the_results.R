# This file performs the following steps:
# 1. Load a sample of recall documents from a CSV file.
# 2. Define the structured output type for extracting manufacturer, models, and model years.
# 3. Define a function to extract structured data from a single document using a specified model
# 4. Define a function to run the extraction for all documents and save the results and runtime summary.
# 5. Run the extraction for seven different models and save the results.


# 1. Load a sample of recall documents from a CSV file
df = readr::read_csv("recalls_sample.csv", locale = readr::locale(encoding = "UTF-8"))

doc_data = df |>
  dplyr::slice_head(n = 30) |>
  dplyr::mutate(document_id = dplyr::row_number()) |>
  dplyr::select(document_id, defect_description)



# 2. Define the structured output type for extracting manufacturer, models, and model years
type_recall = ellmer::type_object(
  manufacturer = ellmer::type_string(
    paste(
      "Manufacturer issuing the recall.",
      "Extract the manufacturer exactly as written at the beginning of the description.",
      "When the text provides both a full company name and a parenthetical short name,",
      "return them as one string in the format: Full company name; Short name.",
      "For example: 'Generic Vehicle Manufacturing Company; GVMC'.",
      "Do not include wording such as 'is recalling'.",
      "Do not infer, expand, correct, translate, or standardize the company name.",
      "If no parenthetical short name is provided, return only the full company name."
    )
  ),

  models = ellmer::type_array(
    ellmer::type_string(
      paste(
        "One affected vehicle model.",
        "Return only the model name or model designation explicitly stated in the text.",
        "Do not include the manufacturer, model year, quantity, or general vehicle category.",
        "Preserve the original spelling, capitalization, punctuation, numbers,",
        "and parenthetical qualifiers.",
        "Create one array element for each distinct model.",
        "Preserve the order in which the models first appear.",
        "Do not combine multiple models into one array element.",
        "Do not infer or create models that are not explicitly stated."
      )
    )
  ),

  model_years = ellmer::type_array(
    ellmer::type_string(
      paste(
        "One affected four-digit model year.",
        "Return each year as a separate array element.",
        "Expand inclusive year ranges into individual years.",
        "For example, '1900-1902' becomes ['1900', '1901', '1902'].",
        "Remove duplicate years.",
        "Return the years in ascending numeric order.",
        "Return only years explicitly stated in the text.",
        "Do not infer unstated years."
      )
    )
  )
)

# 3. Define a function to extract structured data from a single document using a specified model
# The function returns a tibble with the extracted data, success status, error message (if any), runtime, and timestamp.
# The function uses tryCatch to handle errors during the extraction process and records the runtime for each extraction.
# The function takes the following parameters:
# - document_id: Unique identifier for the document.
# - defect_description: The text of the defect description to be processed.
# - model_name: The name of the model to be used for extraction.
# - repeat_id: The identifier for the current repeat iteration.
# - temperature: The temperature parameter for the model (default is 0).

extract_one = function(
  document_id,
  defect_description,
  model_name,
  repeat_id,
  temperature = 0
) {
  
  start_time = Sys.time()
  
  result = tryCatch({
    
    chat = if (identical(model_name, "gpt-5.4-nano")) {
      
      ellmer::chat_openai(
        model = model_name,
        params = ellmer::params(
          temperature = temperature
        )
      )
      
    } else {
      
      ellmer::chat_ollama(
        model = model_name,
        params = ellmer::params(
          temperature = temperature,
          think = FALSE
        )
      )
    }
    
    out = chat$chat_structured(
      defect_description,
      type = type_recall
    )
    
    tibble::tibble(
      document_id = document_id,
      model_name = model_name,
      repeat_id = repeat_id,
      temperature = temperature,
      manufacturer = paste(
        unique(out$manufacturer),
        collapse = "; "
      ),
      models = paste(
        out$models,
        collapse = "; "
      ),
      model_years = paste(
        unique(out$model_years),
        collapse = "; "
      ),
      success = TRUE,
      error_message = NA_character_
    )
    
  }, error = function(e) {
    
    tibble::tibble(
      document_id = document_id,
      model_name = model_name,
      repeat_id = repeat_id,
      temperature = temperature,
      manufacturer = NA_character_,
      models = NA_character_,
      model_years = NA_character_,
      success = FALSE,
      error_message = conditionMessage(e)
    )
  })
  
  end_time = Sys.time()
  
  result |>
    dplyr::mutate(
      runtime_sec = as.numeric(
        difftime(end_time, start_time, units = "secs")
      ),
      chat_timestamp = end_time
    )
}

# 4. Define a function to run the extraction for all documents and save the results and runtime summary.
# The function takes the following parameters:
# - model_name: The name of the model to be used for extraction.
# - doc_data: A data frame containing the document_id and defect_description columns.
# - n_repeats: The number of times to repeat the extraction for each document.
# - temperature: The temperature parameter for the model (default is 0).
# - results_dir: The directory where the results and summary files will be saved (default is the current directory).
# The function validates the inputs, constructs a grid of extraction tasks, runs the extraction for each task, saves the results to a CSV file, and summarizes the runtime and success rates in another CSV file.
run_one_model = function(
  model_name,
  doc_data,
  n_repeats,
  temperature = 0,
  results_dir = "results/"
) {
  
  # ------------------------------------------------------------------
  # Validate inputs
  # ------------------------------------------------------------------
  
  required_columns = c(
    "document_id",
    "defect_description"
  )
  
  missing_columns = setdiff(
    required_columns,
    names(doc_data)
  )
  
  if (length(missing_columns) > 0) {
    stop(
      "doc_data is missing required column(s): ",
      paste(missing_columns, collapse = ", ")
    )
  }
  
  if (
    length(model_name) != 1 ||
    is.na(model_name) ||
    !nzchar(trimws(model_name))
  ) {
    stop("model_name must be one non-empty character string.")
  }
  
  if (
    length(n_repeats) != 1 ||
    is.na(n_repeats) ||
    n_repeats < 1 ||
    n_repeats != as.integer(n_repeats)
  ) {
    stop("n_repeats must be a positive integer.")
  }
  
  if (anyDuplicated(doc_data$document_id) > 0) {
    stop("document_id must uniquely identify each row in doc_data.")
  }
  
  if (anyNA(doc_data$document_id)) {
    stop("document_id cannot contain missing values.")
  }
  
  # Ensure the output directory exists
  dir.create(
    results_dir,
    recursive = TRUE,
    showWarnings = FALSE
  )
  
  # Create a file-safe version of the model name
  safe_model_name = gsub(
    pattern = "[^A-Za-z0-9._-]+",
    replacement = "_",
    x = model_name
  )
  
  # ------------------------------------------------------------------
  # Construct the extraction grid
  # ------------------------------------------------------------------
  
  run_grid = tidyr::crossing(
    repeat_id = seq_len(n_repeats),
    document_id = doc_data$document_id
  ) |>
    dplyr::left_join(
      doc_data |>
        dplyr::select(
          document_id,
          defect_description
        ),
      by = "document_id"
    ) |>
    dplyr::mutate(
      model_name = model_name,
      temperature = temperature,
      .before = 1
    )
  
  # ------------------------------------------------------------------
  # Run each extraction
  # ------------------------------------------------------------------
  
  results = purrr::pmap_dfr(
    run_grid,
    function(
      model_name,
      temperature,
      repeat_id,
      document_id,
      defect_description
    ) {
      extract_one(
        document_id = document_id,
        defect_description = defect_description,
        model_name = model_name,
        repeat_id = repeat_id,
        temperature = temperature
      )
    },
    .progress = paste("Running", model_name)
  )
  
  # ------------------------------------------------------------------
  # Save extraction results
  # ------------------------------------------------------------------
  
  results_file = file.path(
    results_dir,
    paste0(
      "recalls_extracted_",
      safe_model_name,
      ".csv"
    )
  )
  
  readr::write_csv(
    results,
    results_file,
    na = ""
  )
  
  # ------------------------------------------------------------------
  # Summarize runtime and success
  # ------------------------------------------------------------------
  
  runtime_summary = results |>
    dplyr::group_by(
      model_name,
      temperature
    ) |>
    dplyr::summarise(
      n_documents = dplyr::n_distinct(document_id),
      n_repeats = dplyr::n_distinct(repeat_id),
      n_extractions = dplyr::n(),
      n_success = sum(success, na.rm = TRUE),
      n_failure = sum(!success, na.rm = TRUE),
      success_rate = mean(success, na.rm = TRUE),
      total_runtime_sec = sum(runtime_sec, na.rm = TRUE),
      mean_runtime_per_extraction_sec = mean(
        runtime_sec,
        na.rm = TRUE
      ),
      median_runtime_per_extraction_sec = stats::median(
        runtime_sec,
        na.rm = TRUE
      ),
      mean_total_runtime_per_document_sec =
        total_runtime_sec / n_documents,
      .groups = "drop"
    )
  
  summary_file = file.path(
    results_dir,
    paste0(
      "runtime_summary_",
      safe_model_name,
      ".csv"
    )
  )
  
  readr::write_csv(
    runtime_summary,
    summary_file,
    na = ""
  )
  
  results
}

# 5. Run the extraction for seven different models and save the results.
## A. Run the extraction for the "llama3.2:3b" model 
results_llama32_3b = run_one_model(
  model_name = "llama3.2:3b",
  doc_data = doc_data,
  n_repeats = 5
)

## B. Run the extraction for the "llama3.2:1b" model
results_llama32_1b = run_one_model(
  model_name = "llama3.2:1b",
  doc_data = doc_data,
  n_repeats = 5
)

## C. Run the extraction for the "granite4.1:8b" model
results_grantite8b = run_one_model(
  model_name = "granite4.1:8b",
  doc_data = doc_data,
  n_repeats = 5
)

## D. Run the extraction for the "granite4.1:3b" model
results_grantite3b = run_one_model(
  model_name = "granite4.1:3b",
  doc_data = doc_data,
  n_repeats = 5
)

# E. Run the extraction for the "gemma4:e2b" model
results_gemmae2b = run_one_model(
   model_name = "gemma4:e2b",
   doc_data = doc_data,
   n_repeats = 5 
)

# F. Run the extraction for the "phi4-mini" model
results_phi4_mini = run_one_model(
   model_name = "phi4-mini",
   doc_data = doc_data,
   n_repeats = 5 
)

# G. Run the extraction for the "gpt-5.4-nano" model
Sys.getenv("OPENAI_API_KEY")
results_gp54_nano = run_one_model(
   model_name = "gpt-5.4-nano", # gpt-5.4-nano-2026-03-17
   doc_data = doc_data,
   n_repeats = 5 
)
