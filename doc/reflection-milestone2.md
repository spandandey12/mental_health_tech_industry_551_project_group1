# Milestone 2 Reflection

## What we have implemented

For Milestone 2, we built a working prototype of an interactive dashboard to explore workplace mental health survey data using Dash and Altair. The dashboard is made to help users explore treatment outcomes and workplace-related factors across different demographic and company groups.

The current version includes:

All plots are coordinated through shared Dash callbacks, ensuring consistent filtering across visualizations and summary metrics. The interface is self-documenting, with descriptive titles, legends, and explanatory text embedded directly in the dashboard.

## What is not yet implemented

Some functionality described in the original proposal has not yet been implemented. In particular:
- Additional workplace support indicators and alternative grouping dimensions are not yet included.
- Cross-year comparative views and trend-focused visualizations are planned for later milestones.
- Advanced UI refinements and layout customization are not yet implemented.

These features will be added in future milestones after getting feedback from the TA.

## Known limitations and issues

Deployment to a public hosting platform is still in progress. The app works properly on a local machine, but the final deployment is delayed because of repository permission issues. This will be fixed in a future milestone.

Also, the code currently shows some small pandas `FutureWarning` messages because of outdated functions. These warnings do not affect how the dashboard works and will be cleaned up later.

## Strengths, limitations, and future improvements

One of the main strengths of the dashboard is its clear layout and interactive features, which make it easy to explore the connection between mental health treatment and workplace conditions across different categories. The KPI cards along with multiple charts help users understand both the overall picture and the details.

Right now, the dashboard has a limited number of charts and not many customization options for users. In the next milestones, we plan to add more analysis options, improve the visual design based on feedback, make deployment more stable, and improve the overall user experience and performance.
