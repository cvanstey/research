# Italy Population & Migration Analysis
# output: html_notebook  (if running as an R Notebook; otherwise run as script)

library(sf)
library(tidyverse)
library(janitor)
library(readxl)
library(scales)
library(patchwork)
library(ggridges)
library(ggrepel)
library(fable)
library(tsibble)
library(feasts)

clean_key <- function(x) {
  x %>%
    str_trim() %>%
    str_to_lower() %>%
    str_replace_all("[[:space:]]+", "_") %>%
    str_replace_all("[^a-z0-9_]", "")
}

# ─────────────────────────────────────────
# LOAD SHAPEFILES
# ─────────────────────────────────────────

italy_0 <- st_read("C:/Users/crook/Documents/DSSA Program/Italy Map Files/gadm41_ITA_0.shp", quiet = TRUE)
italy_1 <- st_read("C:/Users/crook/Documents/DSSA Program/Italy Map Files/gadm41_ITA_1.shp", quiet = TRUE)
italy_2 <- st_read("C:/Users/crook/Documents/DSSA Program/Italy Map Files/gadm41_ITA_2.shp", quiet = TRUE)

italy_0 <- st_transform(italy_0, 4326)
italy_1 <- st_transform(italy_1, 4326)
italy_2 <- st_transform(italy_2, 4326)

ggplot() +
  geom_sf(data = italy_0, fill = "gray95", color = "black", linewidth = 1) +
  geom_sf(data = italy_1, fill = NA, color = "gray40", linewidth = 0.5) +
  geom_sf(data = italy_2, fill = NA, color = "gray70", linewidth = 0.2) +
  theme_void()

# ─────────────────────────────────────────
# ISTAT POPULATION DATA
# ─────────────────────────────────────────

data_dir <- "C:/Users/crook/Documents/DSSA Program/data-CVAnstey/Data Exploration/Data"

istat <- list.files(data_dir, pattern = "DCIS_POPRES1.*\\.csv$", full.names = TRUE) %>%
  map(~ read_csv(.x,
                 locale = locale(encoding = "UTF-8"),
                 show_col_types = FALSE) %>%
        clean_names()) %>%
  list_rbind() %>%
  mutate(time_period = as.integer(time_period)) %>%
  filter(time_period < 2026)   # drop the metadata row

# Check what you have
istat %>% count(time_period)

# Verify
nrow(istat)
istat %>% count(time_period) %>% print(n = 30)
istat %>% distinct(territory) %>% print(n = 30)

regions_to_exclude_clean <- clean_key(c(
  "Nord-ovest","Nord-est","Centro","Sud","Isole",
  "Centro (I)",
  "Piemonte","Liguria","Lombardia",
  "Veneto","Friuli-Venezia Giulia",
  "Emilia-Romagna","Toscana","Umbria","Marche","Lazio",
  "Abruzzo","Molise","Campania","Puglia",
  "Basilicata","Calabria","Sicilia","Sardegna",
  "Trentino-Alto Adige/Südtirol"
))

istat_prov <- istat %>%
  filter(
    indicator == "Population on 1st January",
    sex == 9,
    age == "TOTAL",
  ) %>%
  filter(!str_detect(territory, regex("january|female|estimate", ignore_case = TRUE))) %>%
  mutate(tmp = clean_key(territory)) %>%
  filter(!tmp %in% regions_to_exclude_clean) %>%
  select(-tmp) %>%
  group_by(territory, time_period) %>%
  summarise(
    population = sum(as.numeric(observation), na.rm = TRUE),
    .groups = "drop"
  ) %>%
  mutate(province_clean = clean_key(territory))

italy_2 <- italy_2 %>%
  mutate(province_clean = clean_key(NAME_2))

italy_prov_map <- italy_2 %>%
  left_join(
    istat_prov %>% select(province_clean, time_period, population),
    by = "province_clean"
  )

ggplot(italy_prov_map) +
  geom_sf(aes(fill = population), color = NA) +
  scale_fill_viridis_c(labels = comma, na.value = "white") +
  theme_void() +
  labs(title = "Italy: Population by Province", fill = "Population")

# ─────────────────────────────────────────
# UN DESA MIGRATION DATA
# ─────────────────────────────────────────

undesa_raw <- read_excel(
  "C:/Users/crook/PROJECTS/PythonProject_OCR/scans/undesa_pd_2024_ims_stock_by_sex_destination_and_origin.xlsx",
  sheet = "Table 1",
  skip = 10,
  col_types = "text"
) %>%
  clean_names() %>%
  filter(if_any(everything(), ~ !is.na(.x) & .x != "")) %>%
  mutate(across(everything(), str_squish))

dest_col   <- "region_development_group_country_or_area_of_destination"
origin_col <- "region_development_group_country_or_area_of_origin"

# ─────────────────────────────────────────
# EXTRACT TOTAL MIGRATION
# ─────────────────────────────────────────

get_total_col <- function(df, year) {
  names(df)[8:15][str_detect(names(df)[8:15], as.character(year))][1]
}

extract_totals <- function(df) {
  total_cols <- names(df)[8:15]
  
  df %>%
    select(all_of(total_cols)) %>%
    summarise(across(everything(), ~ sum(as.numeric(.x), na.rm = TRUE))) %>%
    pivot_longer(everything(), names_to = "year_raw", values_to = "stock") %>%
    mutate(year = as.integer(str_extract(year_raw, "\\d{4}"))) %>%
    select(year, stock)
}

italy_as_dest <- undesa_raw %>%
  filter(str_detect(.data[[dest_col]], regex("^italy$", ignore_case = TRUE)))

italy_as_origin <- undesa_raw %>%
  filter(str_detect(.data[[origin_col]], regex("^italy$", ignore_case = TRUE)))

crossover <- bind_rows(
  extract_totals(italy_as_dest) %>% mutate(direction = "Immigrants into Italy"),
  extract_totals(italy_as_origin) %>% mutate(direction = "Italians living abroad")
)

ggplot(crossover, aes(year, stock, color = direction)) +
  geom_line(linewidth = 1.4) +
  geom_point(size = 3) +
  scale_y_continuous(labels = comma) +
  scale_x_continuous(breaks = c(1990,1995,2000,2005,2010,2015,2020,2024)) +
  scale_color_manual(values = c("#E69F00","#0072B2")) +
  theme_minimal() +
  labs(
    title = "Italy's Migration Crossover",
    subtitle = "1990–2024",
    y = "Migrant stock",
    x = NULL
  )

# ─────────────────────────────────────────
# TOP ORIGIN COUNTRIES
# ─────────────────────────────────────────

col_2024 <- get_total_col(undesa_raw, 2024)

top_origins <- undesa_raw %>%
  filter(str_detect(.data[[dest_col]], regex("^italy$", ignore_case = TRUE))) %>%
  filter(!str_detect(.data[[origin_col]], regex(
    "world|region|africa|europe|asia|america|oceania|developed|developing|income",
    ignore_case = TRUE
  ))) %>%
  mutate(stock_2024 = as.numeric(.data[[col_2024]])) %>%
  select(country = all_of(origin_col), stock_2024) %>%
  filter(!is.na(stock_2024), stock_2024 > 0) %>%
  slice_max(stock_2024, n = 10)

ggplot(top_origins, aes(
  x = stock_2024,
  y = reorder(country, stock_2024)
)) +
  geom_col(fill = "#457B9D") +
  geom_text(aes(label = comma(stock_2024)), hjust = -0.1) +
  scale_x_continuous(labels = comma, expand = expansion(mult = c(0,0.15))) +
  theme_minimal() +
  labs(
    title = "Top 10 Origins of Immigrants in Italy (2024)",
    x = "Migrant stock",
    y = NULL
  )


# Italy Population Analysis — Extended ggplot Suite
# New packages needed:
#   install.packages(c("patchwork","ggridges","ggrepel","fable","tsibble","feasts"))



# ─────────────────────────────────────────
# 1. POPULATION CHANGE CHOROPLETH (2019 → 2024)
# ─────────────────────────────────────────
year_start <- 2019
year_end   <- 2024

pop_start_df <- istat_prov %>%
  filter(time_period == year_start, !is.na(population)) %>%
  group_by(province_clean, territory) %>%
  summarise(pop_start = sum(population), .groups = "drop")

pop_end_df <- istat_prov %>%
  filter(time_period == year_end, !is.na(population)) %>%
  group_by(province_clean, territory) %>%
  summarise(pop_end = sum(population), .groups = "drop")

pop_change <- pop_start_df %>%
  left_join(pop_end_df, by = c("province_clean", "territory")) %>%
  mutate(pct_change = (pop_end - pop_start) / pop_start * 100)

# Verify it worked
glimpse(pop_change)

italy_change_map <- italy_2 %>%
  left_join(pop_change, by = "province_clean")

p_change <- ggplot(italy_change_map) +
  geom_sf(aes(fill = pct_change), color = "white", linewidth = 0.15) +
  scale_fill_gradient2(
    low = "#D7191C", mid = "gray95", high = "#2C7BB6", midpoint = 0,
    labels = label_number(suffix = "%"), na.value = "gray80", name = "Change"
  ) +
  theme_void() +
  labs(
    title    = "Population Change by Province",
    subtitle = paste0(year_start, " → ", year_end, " · red = decline, blue = growth")
  ) +
  theme(
    plot.title    = element_text(face = "bold", size = 13),
    plot.subtitle = element_text(size = 10, color = "gray40")
  )

# ─────────────────────────────────────────
# 2. FACETED SMALL-MULTIPLE MAPS
# ─────────────────────────────────────────

facet_years <- c(2019, 2020, 2022, 2024)

facet_data <- italy_2 %>%
  left_join(
    istat_prov %>%
      filter(time_period %in% facet_years) %>%
      select(province_clean, time_period, population),
    by = "province_clean"
  )

p_facet <- ggplot(facet_data) +
  geom_sf(aes(fill = population), color = NA) +
  scale_fill_viridis_c(
    labels   = label_number(scale = 1e-3, suffix = "k"),
    na.value = "gray90", option = "magma", direction = -1,
    name = "Population"
  ) +
  facet_wrap(~ time_period, nrow = 1) +
  theme_void() +
  labs(title = "Province Population Across Four Snapshots") +
  theme(
    plot.title       = element_text(face = "bold", size = 13),
    strip.text       = element_text(face = "bold", size = 10),
    legend.position  = "bottom",
    legend.key.width = unit(2, "cm")
  )

# ─────────────────────────────────────────
# 3. K-MEANS CLUSTERING ON POPULATION TRAJECTORIES
# ─────────────────────────────────────────

pop_wide <- istat_prov %>%
  filter(!is.na(population), population > 0) %>%
  group_by(province_clean, territory, time_period) %>%
  summarise(population = sum(population), .groups = "drop") %>%
  pivot_wider(
    names_from  = time_period,
    values_from = population,
    names_prefix = "y"
  ) %>%
  drop_na()

# Index to 2019 (earliest available year)
base_year_col <- paste0("y", year_start)

pop_norm <- pop_wide %>%
  mutate(across(starts_with("y"), ~ .x / .data[[base_year_col]] * 100))

mat <- pop_norm %>%
  select(starts_with("y")) %>%
  as.matrix()

set.seed(42)
km <- kmeans(mat, centers = 4, nstart = 25)
pop_wide$cluster <- factor(km$cluster)

# Inspect centroids to assign meaningful labels:
# print(km$centers)
cluster_labels <- c(
  "1" = "Steady growth",
  "2" = "Rapid decline",
  "3" = "Stable / flat",
  "4" = "Boom then stall"
)
CLUSTER_COLORS <- c(
  "Steady growth"   = "#2C7BB6",
  "Rapid decline"   = "#D7191C",
  "Stable / flat"   = "#ABDDA4",
  "Boom then stall" = "#FDAE61"
)

italy_clust <- italy_2 %>%
  left_join(pop_wide %>% select(province_clean, cluster), by = "province_clean") %>%
  mutate(cluster_lbl = cluster_labels[as.character(cluster)])

p_cluster <- ggplot(italy_clust) +
  geom_sf(aes(fill = cluster_lbl), color = "white", linewidth = 0.15) +
  scale_fill_manual(values = CLUSTER_COLORS, na.value = "gray85", name = NULL) +
  theme_void() +
  labs(
    title    = "Province Clusters by Population Trajectory",
    subtitle = paste0("K-means (k = 4) on indexed population paths (base = ", year_start, ")")
  ) +
  theme(
    plot.title      = element_text(face = "bold", size = 13),
    plot.subtitle   = element_text(size = 10, color = "gray40"),
    legend.position = "bottom"
  )

pop_long_norm <- pop_norm %>%
  left_join(pop_wide %>% select(province_clean, cluster), by = "province_clean") %>%
  pivot_longer(starts_with("y"), names_to = "year", values_to = "index") %>%
  mutate(year = as.integer(str_remove(year, "^y")))

cluster_centroids <- pop_long_norm %>%
  group_by(cluster, year) %>%
  summarise(index = mean(index), .groups = "drop") %>%
  mutate(cluster_lbl = cluster_labels[as.character(cluster)])

p_trajectories <- ggplot(
  pop_long_norm %>% mutate(cluster_lbl = cluster_labels[as.character(cluster)]),
  aes(year, index, group = province_clean, color = cluster_lbl)
) +
  geom_line(alpha = 0.20, linewidth = 0.35) +
  geom_line(
    data = cluster_centroids,
    aes(year, index, color = cluster_lbl, group = cluster_lbl),
    linewidth = 2.2, inherit.aes = FALSE
  ) +
  scale_color_manual(values = CLUSTER_COLORS, name = "Cluster") +
  scale_x_continuous(breaks = sort(unique(istat_prov$time_period))) +
  theme_minimal() +
  labs(
    title    = "Population Index by Province and Cluster",
    subtitle = paste0("Base = 100 at ", year_start, " · bold lines = cluster centroids"),
    x = NULL, y = "Index (base = 100)"
  ) +
  theme(
    plot.title      = element_text(face = "bold", size = 13),
    plot.subtitle   = element_text(size = 10, color = "gray40"),
    legend.position = "bottom"
  )

# ─────────────────────────────────────────
# 4. RIDGE PLOT (years you actually have)
# ─────────────────────────────────────────

region_lookup <- italy_2 %>%
  st_drop_geometry() %>%
  select(province_clean, region = NAME_1)

pop_with_region <- istat_prov %>%
  left_join(region_lookup, by = "province_clean") %>%
  filter(!is.na(region), !is.na(population))

available_ridge_years <- sort(unique(pop_with_region$time_period))

p_ridge <- ggplot(
  pop_with_region %>% filter(time_period %in% available_ridge_years),
  aes(x = population / 1e3, y = factor(time_period), fill = after_stat(x))
) +
  geom_density_ridges_gradient(
    scale = 2.5, rel_min_height = 0.01, color = "white", linewidth = 0.4
  ) +
  scale_fill_viridis_c(option = "plasma", name = "Pop (k)") +
  scale_x_continuous(labels = label_number(suffix = "k")) +
  theme_ridges() +
  labs(
    title    = "Distribution of Province Populations",
    subtitle = "Rightward shift = concentration in larger provinces",
    x = "Population (thousands)", y = NULL
  ) +
  theme(
    plot.title      = element_text(face = "bold", size = 13),
    plot.subtitle   = element_text(size = 10, color = "gray40"),
    legend.position = "right"
  )

# ─────────────────────────────────────────
# 5. LOLLIPOP: top and bottom movers
# ─────────────────────────────────────────

movers <- bind_rows(
  pop_change %>% filter(!is.na(pct_change)) %>% slice_max(pct_change, n = 8),
  pop_change %>% filter(!is.na(pct_change)) %>% slice_min(pct_change, n = 8)
) %>%
  mutate(
    territory = fct_reorder(territory, pct_change),
    direction = if_else(pct_change >= 0, "Growth", "Decline")
  )

p_lollipop <- ggplot(movers,
                     aes(x = pct_change, y = territory, color = direction)
) +
  geom_segment(aes(x = 0, xend = pct_change, yend = territory),
               linewidth = 0.8) +
  geom_point(size = 3.5) +
  geom_vline(xintercept = 0, color = "gray30", linewidth = 0.4) +
  geom_text(
    aes(label = number(pct_change, accuracy = 0.1, suffix = "%")),
    hjust = ifelse(movers$pct_change >= 0, -0.3, 1.3),
    size  = 3
  ) +
  scale_color_manual(
    values = c("Growth" = "#2C7BB6", "Decline" = "#D7191C"),
    guide  = "none"
  ) +
  scale_x_continuous(
    labels = label_percent(scale = 1),
    expand = expansion(mult = 0.18)
  ) +
  theme_minimal() +
  labs(
    title    = paste0("Biggest Population Movers ", year_start, "–", year_end),
    subtitle = "Top 8 growing and top 8 declining provinces",
    x = "% change", y = NULL
  ) +
  theme(
    plot.title    = element_text(face = "bold", size = 13),
    plot.subtitle = element_text(size = 10, color = "gray40")
  )

# ─────────────────────────────────────────
# 6. PATCHWORK ASSEMBLY
# ─────────────────────────────────────────

(p_change | p_cluster) +
  plot_annotation(
    title = "Italy Province Population — Spatial Summaries",
    theme = theme(plot.title = element_text(face = "bold", size = 16))
  )

(p_trajectories / p_lollipop) +
  plot_annotation(
    title = "Trajectory Clustering & Top Movers",
    theme = theme(plot.title = element_text(face = "bold", size = 16))
  )

p_facet +
  plot_annotation(
    title = "Province Population: Four Snapshots",
    theme = theme(plot.title = element_text(face = "bold", size = 16))
  )

p_ridge