#!/usr/bin/env python3
import boto3
import datetime
from dateutil.relativedelta import relativedelta
import os
import os
import boto3
import logging
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# set logging settings
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


def send_file_to(send_from,send_to,file_to_send,subject):
    

    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = "Attached is the monthly AWS Cost report"

    # The HTML body of the email.
    BODY_HTML = """\
    <html>
    <head></head>
    <body>
    <p>Attached is the monthly AWS Cost report</p>
    </body>
    </html>
    """

    # The character encoding for the email.
    CHARSET = "utf-8"

    # Create a new SES resource and specify a region.
    email_client = boto3.client('ses') #,region_name=AWS_REGION)

    # Create a multipart/mixed parent container.
    msg = MIMEMultipart('mixed')
    # Add subject, from and to lines.
    msg['Subject'] = subject
    msg['From'] = send_from
    msg['To'] = send_to

    # Create a multipart/alternative child container.
    msg_body = MIMEMultipart('alternative')

    # Encode the text and HTML content and set the character encoding. This step is
    # necessary if you're sending a message with characters outside the ASCII range.
    textpart = MIMEText(BODY_TEXT.encode(CHARSET), 'plain', CHARSET)
    htmlpart = MIMEText(BODY_HTML.encode(CHARSET), 'html', CHARSET)

    # Add the text and HTML parts to the child container.
    msg_body.attach(textpart)
    msg_body.attach(htmlpart)

    # Define the attachment part and encode it using MIMEApplication.
    att = MIMEApplication(open(file_to_send, 'rb').read())

    # Add a header to tell the email client to treat this part as an attachment,
    # and to give the attachment a name.
    att.add_header('Content-Disposition','attachment',filename=os.path.basename(file_to_send))

    # Attach the multipart/alternative child container to the multipart/mixed
    # parent container.
    msg.attach(msg_body)

    # Add the attachment to the parent container.
    msg.attach(att)
    #print(msg)
    LOGGER.info(f"sending send method from {send_from} to {send_to} ")
    LOGGER.info(str(msg))
    try:
        #Provide the contents of the email.
        response = email_client.send_raw_email(
            Source=send_from,
            Destinations=[send_to],
            RawMessage={
                'Data':msg.as_string(),
            }
        )
    # Display an error if something goes wrong.	
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])
    
    return


def handler(event, context):

    # get sender and list from env vars via template
    email_sender = os.getenv("EmailSenderAddress")
    email_list = os.getenv("EmailList").split(",")
    cost_threshold = int(os.getenv("CostCutoff"))


    LOGGER.info(["sending from",email_sender])
    LOGGER.info(email_list)
    # get costs for last month
    # if current date is in month 7, then this will report all costs in month 6
    
    
    end = datetime.date.today().replace(day=1)
    start = (datetime.date.today() - relativedelta(months=+1)).replace(day=1) #1st day of month a month ago
    
    # create client
    client = boto3.client('ce')

    # get cost and usage in time period
    response = client.get_cost_and_usage(
                TimePeriod={
                    'Start': start.isoformat(),
                    'End': end.isoformat()
                },
                Granularity='MONTHLY',
                Metrics=[
                    'UnblendedCost',
                ],
                GroupBy=[{"Type":"DIMENSION","Key":"LINKED_ACCOUNT"}]
            )

    # get start and end dates
    start_date = response["ResultsByTime"][0]["TimePeriod"]["Start"]
    end_date = response["ResultsByTime"][0]["TimePeriod"]["End"]
    
    subject = "AWS Cost report for "+start_date+ " to "+end_date
    # create csv file name
    csv_file_name = "cost-report-"+start_date+"-"+end_date+".csv"
    # create csv file path
    csv_path = os.path.join("/tmp",csv_file_name)

    # remove old files if they exist
    try:
        os.remove(csv_path)
    except:
        # file doesnt exist
        pass


    # total cost counter
    total = 0
    # list to sort for cost:id's
    cost_plus_id_list = []

    # create strings of $cost_$id to be sorted
    for result in response["ResultsByTime"][0]["Groups"]:
        LOGGER.info(result)
        # get ID
        id = result["Keys"][0]
        # get cost
        cost = result["Metrics"]["UnblendedCost"]["Amount"]
        # round cost
        cost = str(round(float(cost),2))
        # add to total
        total += float(cost)
        # if cost less than cutoff then ignore its row but add to total
        if float(cost) > cost_threshold:
            cost_plus_id_list.append(cost+"_"+id)

    # sort
    cost_plus_id_list.sort()
    cost_plus_id_list.reverse()

    # match account ID to name
    id_to_name = dict()
    for attribute_dict in response["DimensionValueAttributes"]:
        id_to_name[attribute_dict["Value"]] = attribute_dict["Attributes"]["description"]

    # write new CSV
    with open(csv_path,"a") as csv_file:
        csv_file.write(",".join(["ACCOUNT ID","ACCOUNT NAME","COST"])+"\n")
        for cost_id in cost_plus_id_list:
            cost,id = cost_id.split("_")
            name = id_to_name[id]
            LOGGER.info([id,name,cost])
            csv_file.write(",".join([id,name,cost])+"\n")
        csv_file.write(",".join(["","TOTAL",str(total)]))
    


    LOGGER.info(response)
    
    # send an email to each in email list
    for recipient in email_list:
        LOGGER.info(f"sending to {recipient}")
        send_file_to(email_sender,recipient,csv_path,subject)