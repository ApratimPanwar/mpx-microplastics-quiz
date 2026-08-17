/**
 * MPx Microplastics Quiz — response collector
 *
 * SETUP (one-time, ~5 minutes):
 * 1. Create a new Google Sheet (this will hold your responses).
 * 2. In the Sheet, go to Extensions > Apps Script.
 * 3. Delete any placeholder code and paste in everything below.
 * 4. Click Deploy > New deployment > select type "Web app".
 *      - Execute as: Me
 *      - Who has access: Anyone
 * 5. Click Deploy, authorize the script when prompted, and copy the
 *    Web App URL it gives you.
 * 6. Open the quiz HTML file, find this line near the top of the <script>:
 *        const SUBMIT_URL = "";
 *    and paste your Web App URL between the quotes. Re-share/re-host the
 *    quiz file after saving.
 * 7. Every completed quiz will now append one row to a sheet/tab named
 *    "Responses" in this spreadsheet automatically. The first response
 *    creates the header row from whatever fields it contains; later
 *    responses that introduce a new question automatically get a new
 *    column added.
 *
 * To view live data in the companion Dashboard.html:
 *    File > Share > Publish to web > choose the "Responses" sheet and
 *    CSV format > copy the resulting URL > paste it into the dashboard's
 *    "Fetch" box. Otherwise just download this sheet as CSV periodically
 *    (File > Download > CSV) and drop that file into the dashboard loader.
 */

function doPost(e) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName("Responses");
    if (!sheet) sheet = ss.insertSheet("Responses");

    var data = JSON.parse(e.postData.contents);

    var lastCol = sheet.getLastColumn();
    var headers = lastCol > 0 ? sheet.getRange(1, 1, 1, lastCol).getValues()[0] : [];
    headers = headers.filter(function (h) { return h !== ""; });

    if (headers.length === 0) {
      headers = Object.keys(data);
      sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    } else {
      var newKeys = Object.keys(data).filter(function (k) { return headers.indexOf(k) === -1; });
      if (newKeys.length > 0) {
        headers = headers.concat(newKeys);
        sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
      }
    }

    var row = headers.map(function (h) {
      var v = data[h];
      return (v === undefined || v === null) ? "" : v;
    });
    sheet.appendRow(row);

    return ContentService
      .createTextOutput(JSON.stringify({ status: "ok" }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: "error", message: String(err) }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService.createTextOutput("MPx quiz collector is running. POST responses here.");
}
