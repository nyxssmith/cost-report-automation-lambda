# AWS Cost Report Automation

The cost report generation is done via lambda on AWS.

`template.yaml` is the only file needed for setup and is deployed in the:

```
danieldf@sflscientific.com
#######67 | danieldf@sflscientific.com
```

AWS account.

`lambda.py` contains the same lambda code, but is not used in deployment, as the template has in-line python.

The template will deploy a lambda that runs at 9am on the 1st of each month and will email a cost report to each recipient in the email list

## Parameters

- `EmailSenderAddress`: This is the email address to send from via SES, must be able to receive emails and will be who emails appear to be from. When the template is deployed this email address must quickly click the link in its inbox for verification for the template to deploy.

- `EmailList`: This is a comma separated list of email addresses to get cost report sent to, ex `a@mail.com,b@mail.com`

- `CostCutoff`: This is the number of dollars that if account costs less than, its not given an output row. Its cost is still added to the total, so there will be a discrepancy between total and shown rows

## Example Output

The output report will be a CSV that looks like the following

```csv
ACCOUNT ID,ACCOUNT NAME,COST
##########73,ONE,962.21
##########40,TWO,709.26
##########33,PROJECT_THREE,620.89
##########92,FOUR,379.06
##########67,danieldf@sflscientific.com,287.24
,TOTAL,2962.18
```

And the email will have the subject line `AWS Cost report for 2022-06-01 to 2022-07-01` depending on the month that this was ran during.

## Code Breakdown

The Lambda code that runs will generate a report for the prior month. If ran on any day in April, it will generate a report for the month of March.

The code will make 1 api call to cost explorer to get the costs for all linked accounts, and then once the output.csv is created from the response data, then it will send an individual email to each recipient in the email list.
