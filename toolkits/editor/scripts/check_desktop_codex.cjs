// Historical app-server probe depended on files not shipped in Migu.
// Fail explicitly instead of reading global model credentials or Unix paths.
console.error('This legacy app-server probe is not part of Migu deployment. Use docs/WINDOWS-REPAIR.md and the current host ChatCut list_projects check. No model request was sent.');
process.exitCode = 2;
