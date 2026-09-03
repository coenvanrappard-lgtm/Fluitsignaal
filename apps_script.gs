const SHEET_ID = '1EJLyAMCo_A_WXSO1LpX1MGZBTx8JdjbHColuTTJVUVA';
const STRIPE_SECRET = PropertiesService.getScriptProperties().getProperty('STRIPE_SECRET');
const STRIPE_PRICE_ID = 'price_1TBziPA6IBWxTjTRPD6KwuNp';
const DASHBOARD_URL = 'https://fluitsignaal.com/dashboard.html';

function doGet(e) {
  if (e.parameter.action === 'create_checkout') {
    var email = e.parameter.email;
    if (!email) return response({ error: 'No email' });
    try {
      var res = UrlFetchApp.fetch('https://api.stripe.com/v1/checkout/sessions', {
        method: 'post',
        muteHttpExceptions: true,
        headers: { 'Authorization': 'Bearer ' + STRIPE_SECRET },
        payload: {
          'mode': 'subscription',
          'customer_email': email,
          'line_items[0][price]': STRIPE_PRICE_ID,
          'line_items[0][quantity]': '1',
          'success_url': DASHBOARD_URL + '?email=' + encodeURIComponent(email) + '&upgraded=1',
          'cancel_url': DASHBOARD_URL + '?email=' + encodeURIComponent(email)
        }
      });
      var session = JSON.parse(res.getContentText());
      if (session.url) return response({ url: session.url });
      return response({ error: session.error ? session.error.message : res.getContentText() });
    } catch(err) {
      return response({ error: err.toString() });
    }
  }

  var email = e.parameter.email;
  if (!email) return response({ status: 'ok' });
  var sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName('Users');
  var rows = sheet.getDataRange().getValues();
  var headers = rows[0];
  var emailIdx = headers.indexOf('email');
  for (var i = 1; i < rows.length; i++) {
    if (rows[i][emailIdx].toLowerCase() === email.toLowerCase()) {
      var user = {};
      headers.forEach(function(h, j) { user[h] = rows[i][j]; });
      return response({ found: true, user: user });
    }
  }
  return response({ found: false });
}

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName('Users');
    var rows = sheet.getDataRange().getValues();
    var headers = rows[0];
    var emailIdx = headers.indexOf('email');

    if (data.action === 'update_events') {
      var eventsIdx = headers.indexOf('events');
      for (var i = 1; i < rows.length; i++) {
        if (rows[i][emailIdx].toLowerCase() === data.email.toLowerCase()) {
          sheet.getRange(i + 1, eventsIdx + 1).setValue(data.events);
          return response({ status: 'ok' });
        }
      }
      return response({ error: 'not_found' });
    }

    if (data.action === 'update_notifications') {
      var notifIdx = headers.indexOf('notifications');
      var remindIdx = headers.indexOf('reminders');
      for (var i = 1; i < rows.length; i++) {
        if (rows[i][emailIdx].toLowerCase() === data.email.toLowerCase()) {
          if (notifIdx > -1) sheet.getRange(i + 1, notifIdx + 1).setValue(data.notifications);
          if (remindIdx > -1) sheet.getRange(i + 1, remindIdx + 1).setValue(data.reminders);
          return response({ status: 'ok' });
        }
      }
      return response({ error: 'not_found' });
    }

    // New signup — append row including signup_date
    var today = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd');
    sheet.appendRow([
      data.name,
      data.email,
      data.phone || '',
      data.plan,
      data.events,
      '',                                          // welcome_sent (filled by welcome_email.py)
      data.notifications || 'email',
      data.reminders || 'day_before_email',
      today                                        // signup_date
    ]);
    return response({ status: 'ok' });
  } catch(err) {
    return response({ status: 'error', message: err.toString() });
  }
}

function authorizeUrlFetch() {
  UrlFetchApp.fetch('https://www.google.com');
}

function response(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}
