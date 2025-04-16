import smtplib

def send(receivers, message):
    sender = 'vipin008n@gmail.com'

    message = """From: From Person <vipin008n@gmail.com>
    To: To Person <vipin.n@zyudlylabs.com>
    Subject: SMTP e-mail test

    This is a test e-mail message.
    """

    try:
        smtpObj = smtplib.SMTP('smtp.gmail.com', 587)
        smtpObj.ehlo()
        smtpObj.starttls()
        smtpObj.login(sender, "xxxxxxxxx")   
        smtpObj.sendmail(sender, receivers, message)      
        print ("Successfully sent email")
    except Exception as e:
        print ("Error: unable to send email")
        print (e)
    return "Success"