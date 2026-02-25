# Milestone 2 Reflection

## What we have implemented

For Milestone 2, we built a working prototype of an interactive dashboard to explore workplace mental health survey data using Dash and Altair. The dashboard is made to help users explore treatment outcomes and workplace-related factors across different demographic and company groups.

The current version includes:

* A multi-panel Dash layout with a simple three-column structure (filters on the left, main charts in the center, and notes on the right).
* Interactive global filters for year, region, gender, age group, company size, and remote work status.
* KPI summary cards that show total sample size and some key treatment and support percentages.
* A grouped bar chart that shows mental health treatment rates by demographic group (like age group) and gender.
* A heatmap that shows the relationship between work interference frequency and treatment outcomes.
* Stacked bar charts that compare treatment outcomes across different workplace support factors (like benefits and help-seeking culture).

All the charts update automatically when the user changes the filters. The dashboard is easy to understand because it has clear titles, legends, and short explanations directly on the page.

## What is not yet implemented

Some of the features from the original proposal are not finished yet. In particular:

* More workplace support indicators and additional grouping options are not added yet.
* Comparisons across multiple years and trend visualizations will be added in later milestones.
* Advanced UI improvements and layout changes are also not done yet.

These features will be added in future milestones after getting feedback from the TA.

## Known limitations and issues

Deployment to a public hosting platform is still in progress. The app works properly on a local machine, but the final deployment is delayed because of repository permission issues. This will be fixed in a future milestone.

Also, the code currently shows some small pandas `FutureWarning` messages because of outdated functions. These warnings do not affect how the dashboard works and will be cleaned up later.

## Strengths, limitations, and future improvements

One of the main strengths of the dashboard is its clear layout and interactive features, which make it easy to explore the connection between mental health treatment and workplace conditions across different categories. The KPI cards along with multiple charts help users understand both the overall picture and the details.

Right now, the dashboard has a limited number of charts and not many customization options for users. In the next milestones, we plan to add more analysis options, improve the visual design based on feedback, make deployment more stable, and improve the overall user experience and performance.
