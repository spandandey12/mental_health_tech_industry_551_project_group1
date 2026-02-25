# Milestone 2 Reflection

## What we have implemented

For Milestone 2, we implemented a functional prototype of an interactive dashboard to explore workplace mental health survey data using Dash and Altair. The dashboard is designed to support exploratory analysis of treatment outcomes and workplace factors across different demographic and organizational groups.

The current implementation includes:
- A multi-panel Dash layout with a clear three-column structure (filters, main visualizations, and contextual notes).
- Interactive global filters for year, region, gender, age group, company size, and remote work status.
- KPI summary cards showing sample size and key treatment- and support-related rates.
- A grouped bar chart showing mental health treatment rates by demographic group (e.g., age group) and gender.
- A heatmap visualizing the relationship between work interference frequency and treatment outcomes.
- Stacked bar charts comparing treatment outcomes across workplace support factors (e.g., benefits and help-seeking culture).

All plots are coordinated through shared Dash callbacks, ensuring consistent filtering across visualizations and summary metrics. The interface is self-documenting, with descriptive titles, legends, and explanatory text embedded directly in the dashboard.

## What is not yet implemented

Some functionality described in the original proposal has not yet been implemented. In particular:
- Additional workplace support indicators and alternative grouping dimensions are not yet included.
- Cross-year comparative views and trend-focused visualizations are planned for later milestones.
- Advanced UI refinements and layout customization are not yet implemented.

These features are planned for future milestones after incorporating TA feedback.

## Known limitations and issues

Deployment to a public hosting platform is currently in progress. While the application runs locally and is fully functional, final deployment is pending due to repository permission constraints. This limitation is documented and will be resolved in a future milestone.

Additionally, the current code produces minor pandas `FutureWarning` messages related to deprecated API usage. These warnings do not affect functionality and will be addressed as part of technical cleanup in later milestones.

## Strengths, limitations, and future improvements

A key strength of the current dashboard is its clear structure and coordinated interactivity, which allows users to explore relationships between mental health treatment and workplace conditions across multiple dimensions. The combination of summary KPIs and multiple complementary visualizations supports both high-level and detailed exploration.

Current limitations include a restricted set of visualizations and limited customization options for end users. In future milestones, we plan to expand the range of analyses, refine visual encodings based on feedback, improve deployment robustness, and enhance overall usability and performance.