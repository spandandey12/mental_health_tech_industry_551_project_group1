# Dashboard Proposal: Mental Health in the Tech Industry
## Section 1: Motivation and Purpose

**Our role**: Data science team developing a public facing data visualization tool.

**Target audience:** Individuals interested in understanding mental health trends in the technology industry, including students, tech workers, and the general public.


The tech industry is known to be an environment of speed, long working hours, and high performance demands, which can lead to mental health issues. Though there is much discussion about mental health in the workplace, it is hard to really grasp how company size, benefits availability, remote working, and workplace cultures influence reported mental health.

In order to bridge this existing gap, we are planning to develop an interactive dashboard that would allow users to explore the trends available within the Mental Health in Tech survey data. The proposed dashboard would enable users to filter and compare the information pertaining to mental health and work-related attributes. This would not only raise the overall awareness and provide a platform to engage in an informed discussion on the topic.

---

## 2. Description of the Data

The dataset used for this project is the **Mental Health in Tech Survey**, published by Open Sourcing Mental Illness (OSMI) and publicly available on Kaggle. The survey collects responses from individuals working in the technology sector and focuses on mental health experiences, workplace culture, and organizational support.

The dataset contains responses from over a thousand participants per survey year, and for this project we plan to combine multiple survey years to ensure a sufficiently large sample size. The data includes a mixture of demographic variables (such as age, gender, and country), organizational characteristics (such as company size and whether mental health benefits are provided), and mental health–related variables (such as attitudes toward discussing mental health at work and whether the respondent has sought mental health treatment).

In addition to the original variables provided in the dataset, we may derive new variables to support clearer visualization and analysis. For example, company size may be grouped into broader categories, or countries may be aggregated into regions. These transformations will be documented as part of the exploratory data analysis and data wrangling process. Overall, the dataset provides a rich and relevant foundation for exploring the relationship between workplace context and mental health outcomes in the tech industry.

---

## 3. Research Questions and Usage Scenarios

### Research Questions

1. How does company size relate to the availability of mental health benefits and perceived workplace support in the tech industry?
2. Are employees more likely to seek mental health treatment when mental health discussions are more openly accepted in the workplace?
3. Do attitudes toward mental health and treatment-seeking behavior differ across demographic groups or geographic regions?

### Usage Scenario

Alex is an HR manager at a mid-sized technology company who is responsible for improving employee wellbeing programs. Alex wants to understand how similar organizations approach mental health support and whether certain workplace practices are associated with more positive mental health outcomes.

When Alex opens the dashboard, they first see an overview of key mental health indicators across the tech industry. Using interactive filters, Alex narrows the view to companies of similar size and explores how the availability of mental health benefits varies across regions. By interacting with the visualizations, Alex observes that organizations that encourage open discussions about mental health tend to have higher proportions of employees who report seeking treatment when needed.

Based on these insights, Alex identifies potential areas for improvement within their own organization, such as expanding mental health benefits or implementing initiatives to normalize mental health conversations at work. The dashboard thus supports exploratory analysis and helps translate survey data into actionable organizational insights.

---