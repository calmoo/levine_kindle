## Levine to Kindle fetcher

A Python script that grabs [Matt Levine's Money Stuff Newsletter](https://www.bloomberg.com/opinion/authors/ARbTQlRLRjE/matthew-s-levine), formats it nicely and sends to an Amazon Kindle.

Basic program flow:

- Connects to an email account via IMAP.
- Checks if the newsletter has already been downloaded - exits if so.
- Looks for an IMAP folder called "Matt".
- Gets the HTML body of the latest newsletter.
- Parses to markdown, then to rtf.
- Writes the rtf file to `/files`.
- Attaches rtf and sends to Kindle via SMTP.

## Install dependencies
Tested on Python 3.8 on Ubuntu 18.04.1 - would most likely work on macOS too.
```
python3 -m venv
source venv/bin/activate
pip install -r requirements.txt
curl -L https://github.com/jgm/pandoc/releases/download/2.13/pandoc-2.13-linux-amd64.tar.gz -o pandoc-2.13-linux-amd64.tar.gz
tar xvzf pandoc-2.13-linux-amd64.tar.gz --strip-components 1 -C /usr/local/
```

## Set up cron

The easiest way to run a python script with CRON is to specify the python binary within
the venv directory, as cron uses a shell different to bash and cannot activate the virtual environment.
You will also need to add your `$PATH` to cron, as it does not use the default user's`$PATH` - the pandoc binary
won't be found otherwise.

Edit cron:
```
crontab -e
```
Add these lines:
```
PATH=<output from echo $PATH here>
*/15 15-20 * * 1-5 /path/to/repo/venv/bin/python /path/to/repo/main.py
```
The cron runs every 15 minutes between 3pm and 8pm (system time), Monday - Friday.

## Add config variables

Create a `config.py` file
Add the following variables and fill them in appropriately:
```
imap_host = "imap.gmail.com" ## Default IMAP host for gmail
email_account = "test@test.com" ## This is your email
email_password = "password" ## This is your email password, see note below for gmail
kindle_email = "test@kindlemail.com"
smpt_server = "smtp.gmail.com" Default SMTP host for gmail
```

- For your gmail password, you will probably need a special gmail app password. See instructions [here](https://support.google.com/accounts/answer/185833?hl=en)
- For your Kindle, you'll need to [add your personal email as a trusted sender](https://www.amazon.com/gp/help/customer/display.html?nodeId=GX9XLEVV8G4DB28H)

## Set up Gmail filters:

- This script is naive/lazy and is spoonfed pre-filtered emails to pick off - this avoids awkward IMAP searching.
- You can import the premade filter `email_filter.xml` to your gmail in your account settings [here](https://mail.google.com/mail/u/0/?hl=en&shva=1#settings/filters).
This will create a label called "Matt" with all the newsletters.