====================================================
Stock Scanner : WorkFlow engine for scanner hardware
====================================================

How does it work ?
==================

On start-up, the client lists available scenarii.
When the user selects a scenario, the current scenario and step are stored on the hardware configuration's entry in OpenERP.

When the client sends a message to the server, the next step is selected depending on the current step and the message sent.
Then, the server returns the result of the step, which contains the step type code and the text to display on the hardware screen.
Unlike the standard OpenERP Workflow, each step needs to find a valid transition, because a step needs to be displayed on the hardware screen at all times.

Installation
============

If you plan to use the specific "sentinel.py", you will need the "openobject-library" Python module.

.. note::

   You must use openobject-library earlier than 2.0 with OpenERP v7.
   The version 2.0 of openobject-library only implements the Net-RPC protocol, which was removed from v7.

To test the module, some demo scenarii are available in the `demo` directory of the module.

Configuration
=============

In OpenERP : Declare hardware
-----------------------------

You have to declare some hardware scanners in OpenERP.

Go to "Warehouse > Configuration > Scanner Hardware" and create a new record.

The "step type code" sent by the "sentinel.py" client at start-up is the IP address of the hardware, if connected through SSH.

For the sentinel.py client
--------------------------

The sentinel.py client uses a config file named `.oerpsentinelrc`, using the standard `ini` format.

This file simply contains information for server connection (hostname, port, username, password and database).

Writing scenarii
================

Creation
--------

The preferred way to start the creation of a scenario is to create steps and transitions in diagram view.

Once your steps are created, you can write python code directly from OpenERP, or you can export the scenario to write the python code with your preferred code editor.

In the python code of each step, some variables are available :
    - cr : Cursor to the database
    - uid : ID of the user executing the step (user used to log in with the sentinel, or user configured on the hardware, if any)
    - pool : Pooler to the database
    - model : Pooler on the model configured on the scenario
    - context : Context used on the step
    - m or message : Last message sent by the hardware
    - t or terminal : Browse record on the hardware executing the step
    - tracer : Value of the tracer of the used transition to access this step
    - wkf or workflow : Workflow service
    - scenario : Browse record on the current scenario for the hardware

Some of these variables are also available on transition conditions execution.

As stated previously, the step must always return :
- A step type code, in the `act` variable
- A message to display on the hardware screen, in the `res` variable
- Optionally, a default value, in the `val` variable

Step types
~~~~~~~~~~

The step types are mostly managed by the client.

The standard step types are :

- M : Simple message
- F : Final step, like M, but ends the scenario
- T : Text input
- N : Number input (integer)
- Q : Quantity input (float)
- L : List
- E : Error message, like M, but displayed with different colors
- C : Confirm input
- A : Automatic step. This type is used to automatically execute the next step

.. note::

   The automatic step often needs to define a value in `val`, corresponding to the value the user must send.
   This step type is generally used as replacement of another type, at the end of the step code, by redefining the `act` variable in some cases, for example when a single value is available for a list step.

Import and export
-----------------

The import and export scripts are in the `script` directory of the module

A scenario is exported as a set of files, containing :
    - scenario.xml : Global description of the scenario (name, warehouses, steps, transitions, etc.)
    - A .py file per step : The name of the file is the uuid of the step

Using a test file
-----------------

When developing scenarios, you will often have the same steps to run.
The sentinel.py client allows you to supply a file, which contains the keys pressed during the scenario.

You can define the file to use in the configuration file, on the "test_file" key.
This file will be read instead of calling the curses methods when the scenario is waiting for a user input (including line feed characters).
When the file has been fully read, the client exits.

A sample test file can be found in the "Step Types" demo scenario.

*Special keys* :
For special keys (arrows, delete, etc.), you must write a line containing ':', followed by the curses key code.

Valid key codes are :
    - KEY_DOWN : Down arrow
    - KEY_UP : Up arrow
    - KEY_LEFT : Left arrow
    - KEY_RIGHT : Right arrow
    - KEY_BACKSPACE : Backspace
    - KEY_DC : Delete

