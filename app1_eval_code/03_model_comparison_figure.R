# This file performs the following steps:
# 1. Load the model-level consistency results (from 02) and runtime summaries (from 01).
# 2. Record reference information per model: size on disk and API pricing.
# 3. Assemble one metric table with the four ranking dimensions.
# 4. Define a ranked-bar panel builder (shared look for all four metrics).
# 5. Build the four panels, combine them, and save the figure.
#
# Run 02_intra_model_consistency.R first: this script reads
# results/consistency_by_model.csv.
#
# Figure design notes:
# - Four small multiples, one per metric, each sorted so the best model is on
#   top; the y-axis order IS the ranking for that metric.
# - Values are direct-labeled on every bar, so axes and gridlines are dropped.
# - One hue for all bars (identity is carried by the model names on the axis);
#   labels and text use ink colors, never the bar color.


# 1. Load the model-level consistency results and runtime summaries
consistency_by_model = readr::read_csv(
  "results/consistency_by_model.csv",
  col_types = readr::cols(
    model_name = readr::col_character(),
    .default = readr::col_double()
  )
)

# Runtimes are computed from the raw extraction results (rather than the
# runtime_summary files) so that, for models with failed extractions, the
# mean runtime excluding failures is also available.
runtime_by_model = purrr::map_dfr(
  list.files(
    path = "results/",
    pattern = "^recalls_extracted_.*\\.csv$",
    full.names = TRUE
  ),
  function(file) {
    readr::read_csv(
      file,
      col_types = readr::cols_only(
        model_name = readr::col_character(),
        success = readr::col_logical(),
        runtime_sec = readr::col_double()
      )
    )
  }
) |>
  dplyr::summarise(
    mean_runtime_sec = mean(runtime_sec),
    min_runtime_sec = min(runtime_sec),
    max_runtime_sec = max(runtime_sec),
    mean_runtime_success_sec = mean(runtime_sec[success]),
    n_failures = sum(!success),
    .by = model_name
  )


# 2. Record reference information per model.
# Sizes are the download sizes listed on the Ollama registry
# (ollama.com/library, accessed 2026-07-12). gpt-5.4-nano is API-hosted, so it
# has no local footprint (size NA) but a per-token price; the open-weight
# models are free to run.
model_info = tibble::tribble(
  ~model_name,     ~size_gb, ~usd_per_1m_input, ~usd_per_1m_output,
  "llama3.2:1b",   1.3,      0,                 0,
  "llama3.2:3b",   2.0,      0,                 0,
  "granite4.1:3b", 2.1,      0,                 0,
  "granite4.1:8b", 5.3,      0,                 0,
  "gemma4:e2b",    7.2,      0,                 0,
  "phi4-mini",     2.5,      0,                 0,
  "gpt-5.4-nano",  NA,       0.20,              1.25
)


# 3. Assemble one metric table with the four ranking dimensions
model_metrics = consistency_by_model |>
  dplyr::select(model_name, prop_fully_consistent_docs) |>
  dplyr::left_join(runtime_by_model, by = "model_name") |>
  dplyr::left_join(model_info, by = "model_name") |>
  dplyr::mutate(
    usd_per_1m_tokens = usd_per_1m_input + usd_per_1m_output
  )


# 4. Define a ranked-bar panel builder.
# Emphasis coloring: the winning model wears Miami red (#C41230) in every
# panel; all other models are de-emphasized in warm gray (#CCC9B8).
# Text uses ink colors: primary #0b0b0b, secondary #52514e, baseline #c3c2b7.
winning_model = "gemma4:e2b"

# The optional inner_value / inner_label pair draws a narrow dark bar inside
# the main bar (e.g. a mean recomputed without failed extractions), with its
# value printed just after it, on the main bar. Keep inner_label short (just
# the value): anything wordy belongs in a second line of the main label, so
# the two texts cannot collide inside the bar. Rows where inner_value is NA
# get no inner bar, so the overlay only appears for the models it applies to.
plot_ranked_bars = function(
  data,
  value,
  label,
  title,
  higher_is_better = FALSE,
  inner_value = NULL,
  inner_label = NULL
) {

  inner_value_quo = rlang::enquo(inner_value)
  inner_label_quo = rlang::enquo(inner_label)

  # Order rows worst (bottom) to best (top); among tied values the winning
  # model sorts last, i.e. on top of its tie group.
  data = data |>
    dplyr::mutate(
      value = dplyr::coalesce({{ value }}, 0),
      label = {{ label }}
    ) |>
    dplyr::arrange(
      if (higher_is_better) value else dplyr::desc(value),
      model_name == winning_model
    ) |>
    dplyr::mutate(
      model_name = factor(model_name, levels = model_name)
    )

  p = ggplot2::ggplot(
    data,
    ggplot2::aes(x = value, y = model_name)
  ) +
    ggplot2::geom_col(
      ggplot2::aes(fill = model_name == winning_model),
      width = 0.55,
      show.legend = FALSE
    ) +
    ggplot2::scale_fill_manual(
      values = c(`TRUE` = "#C41230", `FALSE` = "#CCC9B8")
    )

  if (!rlang::quo_is_null(inner_value_quo)) {

    inner_data = data |>
      dplyr::mutate(
        inner_value = !!inner_value_quo,
        inner_label = !!inner_label_quo
      ) |>
      dplyr::filter(!is.na(inner_value))

    if (nrow(inner_data) > 0) {
      p = p +
        ggplot2::geom_col(
          data = inner_data,
          ggplot2::aes(x = inner_value),
          width = 0.22,
          fill = "#52514e"
        ) +
        ggplot2::geom_text(
          data = inner_data,
          ggplot2::aes(x = inner_value, label = inner_label),
          hjust = -0.12,
          size = 2.9,
          color = "#52514e"
        )
    }
  }

  p +
    ggplot2::geom_text(
      ggplot2::aes(
        label = label,
        color = model_name == winning_model
      ),
      hjust = -0.15,
      size = 3.1,
      show.legend = FALSE
    ) +
    ggplot2::scale_color_manual(
      values = c(`TRUE` = "#C41230", `FALSE` = "#52514e")
    ) +
    ggplot2::scale_x_continuous(
      limits = c(0, max(data$value) * 1.5),
      expand = c(0, 0)
    ) +
    ggplot2::labs(title = title) +
    ggplot2::theme_minimal(base_size = 11) +
    ggplot2::theme(
      panel.grid = ggplot2::element_blank(),
      axis.text.x = ggplot2::element_blank(),
      axis.title = ggplot2::element_blank(),
      axis.text.y = ggplot2::element_text(
        color = ifelse(
          levels(data$model_name) == winning_model,
          "#C41230",
          "#0b0b0b"
        ),
        size = 9.5
      ),
      axis.line.y = ggplot2::element_line(color = "#c3c2b7", linewidth = 0.4),
      plot.title = ggplot2::element_text(
        size = 10.5,
        face = "bold",
        color = "#0b0b0b"
      ),
      plot.title.position = "plot"
    )
}


# 5. Build the four panels, combine them, and save the figure
panel_consistency = model_metrics |>
  plot_ranked_bars(
    value = prop_fully_consistent_docs,
    label = scales::percent(prop_fully_consistent_docs, accuracy = 1),
    title = "Consistency: % of documents with all three fields\nidentical across 5 repeats (higher is better)",
    higher_is_better = TRUE
  )

# Runtimes are heavy-tailed, so the labels report the observed range rather
# than a standard deviation. Range endpoints of 10 s or more drop the decimal
# to keep the labels compact.
format_seconds = function(x) {
  ifelse(
    x >= 10,
    scales::number(x, accuracy = 1),
    scales::number(x, accuracy = 0.1)
  )
}

panel_speed = model_metrics |>
  plot_ranked_bars(
    value = mean_runtime_sec,
    label = paste0(
      scales::number(mean_runtime_sec, accuracy = 0.1, suffix = " s"),
      " [",
      format_seconds(min_runtime_sec),
      "—",
      format_seconds(max_runtime_sec),
      "]",
      # The second line qualifies the main mean; the dark inner bar (mean
      # excluding failures) is direct-labeled inside the main bar and defined
      # once in the panel title.
      dplyr::if_else(
        n_failures > 0,
        paste0("\nincl. ", n_failures, " failures"),
        ""
      )
    ),
    inner_value = dplyr::if_else(
      n_failures > 0,
      mean_runtime_success_sec,
      NA_real_
    ),
    inner_label = scales::number(
      mean_runtime_success_sec,
      accuracy = 0.1,
      suffix = " s"
    ),
    title = "Speed: mean seconds per extraction [min—max]\n(quicker is better; dark inner bar = mean excl. failures)"
  )

panel_size = model_metrics |>
  plot_ranked_bars(
    value = size_gb,
    label = dplyr::if_else(
      is.na(size_gb),
      paste0(
        "API-hosted — no local copy: not private, not on-prem,\n",
        "and the provider can throttle or discontinue the model"
      ),
      scales::number(size_gb, accuracy = 0.1, suffix = " GB")
    ),
    title = "Size on disk: Ollama download size\n(smaller is better)"
  )

panel_cost = model_metrics |>
  plot_ranked_bars(
    value = usd_per_1m_tokens,
    label = dplyr::if_else(
      usd_per_1m_tokens == 0,
      "$0 — open weights, runs locally",
      paste0(
        scales::dollar(usd_per_1m_input, accuracy = 0.01),
        " in + ",
        scales::dollar(usd_per_1m_output, accuracy = 0.01),
        " out"
      )
    ),
    title = "API price: USD per 1M tokens, input + output\n($0 is preferred)"
  )

comparison_figure = patchwork::wrap_plots(
  panel_consistency,
  panel_speed,
  panel_size,
  panel_cost,
  ncol = 2
) +
  patchwork::plot_annotation(
    title = "Structured extraction models: consistency, speed, size, and cost",
    subtitle = "30 NHTSA recall descriptions × 5 repeats per model, temperature 0; each panel ranked best to worst",
    caption = paste(
      "**Note:** Consistency is a very conservative calculation that primarily leverages the model's consistent interpretation of the extraction scheme:",
      "identical repeats do not mean the model abided by the scheme, and this is not necessarily a measure of accuracy. This is purely the Gage's Repeatability.",
      "**Hardware:** Runtimes were measured on a Windows 11 laptop with an 11th Gen Intel Core i7-1185G7 @ 3.00 GHz, 16 GB RAM, and a standard 128 MB",
      "Intel Iris Xe graphics card (CPU-only inference). **Software:** R 4.6.0 with ellmer 0.4.1; gpt-5.4-nano via the OpenAI API. Run on July 12, 2026.",
      sep = "<br>"
    ),
    theme = ggplot2::theme(
      plot.title = ggplot2::element_text(
        size = 13,
        face = "bold",
        color = "#0b0b0b"
      ),
      plot.subtitle = ggplot2::element_text(size = 10, color = "#52514e"),
      plot.caption = ggtext::element_markdown(
        size = 8.5,
        color = "#52514e",
        hjust = 0,
        lineheight = 1.3
      ),
      plot.caption.position = "plot",
      plot.background = ggplot2::element_rect(fill = "#fcfcfb", color = NA)
    )
  )

ggplot2::ggsave(
  filename = "results/03_model_comparison.png",
  plot = comparison_figure,
  width = 10,
  height = 6.5,
  dpi = 300,
  bg = "#fcfcfb"
)

ggplot2::ggsave(
  filename = "results/03_model_comparison.pdf",
  plot = comparison_figure,
  width = 10,
  height = 6.5,
  bg = "#fcfcfb"
)

comparison_figure
