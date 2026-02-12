# EDA Summary (Raw Data)

- Rows: 1259

- Columns: 27

## Column Types

|                           | dtype   |
|:--------------------------|:--------|
| Timestamp                 | object  |
| Age                       | int64   |
| Gender                    | object  |
| Country                   | object  |
| state                     | object  |
| self_employed             | object  |
| family_history            | object  |
| treatment                 | object  |
| work_interfere            | object  |
| no_employees              | object  |
| remote_work               | object  |
| tech_company              | object  |
| benefits                  | object  |
| care_options              | object  |
| wellness_program          | object  |
| seek_help                 | object  |
| anonymity                 | object  |
| leave                     | object  |
| mental_health_consequence | object  |
| phys_health_consequence   | object  |
| coworkers                 | object  |
| supervisor                | object  |
| mental_health_interview   | object  |
| phys_health_interview     | object  |
| mental_vs_physical        | object  |
| obs_consequence           | object  |
| comments                  | object  |


## Missing Rate (Top 20)

|                           |   missing_% |
|:--------------------------|------------:|
| comments                  |       86.97 |
| state                     |       40.91 |
| work_interfere            |       20.97 |
| self_employed             |        1.43 |
| Gender                    |        0    |
| Timestamp                 |        0    |
| Age                       |        0    |
| family_history            |        0    |
| treatment                 |        0    |
| no_employees              |        0    |
| Country                   |        0    |
| remote_work               |        0    |
| tech_company              |        0    |
| care_options              |        0    |
| benefits                  |        0    |
| seek_help                 |        0    |
| anonymity                 |        0    |
| leave                     |        0    |
| wellness_program          |        0    |
| mental_health_consequence |        0    |


## Categorical Value Counts (sample)

### Timestamp

| value               |   count |
|:--------------------|--------:|
| 2014-08-27 12:43:28 |       2 |
| 2014-08-27 15:55:07 |       2 |
| 2014-08-27 12:54:11 |       2 |
| 2014-08-27 12:44:51 |       2 |
| 2014-08-27 12:37:50 |       2 |
| 2014-08-27 15:24:47 |       2 |
| 2014-08-27 17:33:52 |       2 |
| 2014-08-27 15:23:51 |       2 |
| 2014-08-27 12:31:41 |       2 |
| 2014-08-27 14:22:43 |       2 |


### Gender

| value   |   count |
|:--------|--------:|
| Male    |     615 |
| male    |     206 |
| Female  |     121 |
| M       |     116 |
| female  |      62 |
| F       |      38 |
| m       |      34 |
| f       |      15 |
| Make    |       4 |
| Male    |       3 |


### Country

| value          |   count |
|:---------------|--------:|
| United States  |     751 |
| United Kingdom |     185 |
| Canada         |      72 |
| Germany        |      45 |
| Netherlands    |      27 |
| Ireland        |      27 |
| Australia      |      21 |
| France         |      13 |
| India          |      10 |
| New Zealand    |       8 |


### state

| value     |   count |
|:----------|--------:|
| <missing> |     515 |
| CA        |     138 |
| WA        |      70 |
| NY        |      57 |
| TN        |      45 |
| TX        |      44 |
| OH        |      30 |
| IL        |      29 |
| PA        |      29 |
| OR        |      29 |


### self_employed

| value     |   count |
|:----------|--------:|
| No        |    1095 |
| Yes       |     146 |
| <missing> |      18 |


### family_history

| value   |   count |
|:--------|--------:|
| No      |     767 |
| Yes     |     492 |


### treatment

| value   |   count |
|:--------|--------:|
| Yes     |     637 |
| No      |     622 |


### work_interfere

| value     |   count |
|:----------|--------:|
| Sometimes |     465 |
| <missing> |     264 |
| Never     |     213 |
| Rarely    |     173 |
| Often     |     144 |


### no_employees

| value          |   count |
|:---------------|--------:|
| 6-25           |     290 |
| 26-100         |     289 |
| More than 1000 |     282 |
| 100-500        |     176 |
| 1-5            |     162 |
| 500-1000       |      60 |


### remote_work

| value   |   count |
|:--------|--------:|
| No      |     883 |
| Yes     |     376 |

