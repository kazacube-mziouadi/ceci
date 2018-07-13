# -*- coding: utf-8 -*-


PRINTER_STATES = [
    ('3', 'Idle'),
    ('4', 'Printing'),
    ('5', 'Stopped'),
]

JOB_STATES = [
    ('3', 'Pending'),
    ('4', 'Pending Held'),
    ('5', 'Processing'),
    ('6', 'Processing Stopped'),
    ('7', 'Canceled'),
    ('8', 'Aborted'),
    ('9', 'Completed'),
]

JOB_STATE_REASONS = [
    ('none', 'No reason'),
    ('aborted-by-system', 'Aborted by the system'),
    ('compression-error', 'Error in the compressed data'),
    ('document-access-error', 'The URI cannot be accessed'),
    ('document-format-error', 'Error in the document'),
    ('job-canceled-at-device', 'Cancelled at the device'),
    ('job-canceled-by-operator', 'Cancelled by the printer operator'),
    ('job-canceled-by-user', 'Cancelled by the user'),
    ('job-completed-successfully', 'Completed successfully'),
    ('job-completed-with-errors', 'Completed with some errors'),
    ('job-completed(with-warnings', 'Completed with some warnings'),
    ('job-data-insufficient', 'No data has been received'),
    ('job-hold-until-specified', 'Currently held'),
    ('job-incoming', 'Files are currently being received'),
    ('job-interpreting', 'Currently being interpreted'),
    ('job-outgoing', 'Currently being sent to the printer'),
    ('job-printing', 'Currently printing'),
    ('job-queued', 'Queued for printing'),
    ('job-queued-for-marker', 'Printer needs ink/marker/toner'),
    ('job-restartable', 'Can be restarted'),
    ('job-transforming', 'Being transformed into a different format'),
    ('printer-stopped', 'Printer is stopped'),
    ('printer-stopped-partly', 'Printer state reason set to \'stopped-partly\''),
    ('processing-to-stop-point', 'Cancelled, but printing already processed pages'),
    ('queued-in-device', 'Queued at the output device'),
    ('resources-are-not-ready', 'Resources not available to print the job'),
    ('service-off-line', 'Held because the printer is offline'),
    ('submission-interrupted', 'Files were not received in full'),
    ('unsupported-compression', 'Compressed using an unknown algorithm'),
    ('unsupported-document-format', 'Unsupported format'),
]
