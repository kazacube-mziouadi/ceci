from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from behave.reporter.base import Reporter
from behave.matchers import ParseMatcher, use_step_matcher, matcher_mapping
import tempfile
try:
    import openerp
except ImportError:
    pass
import re

class WithVariablesParseMatcher(ParseMatcher):
    def check_match(self, step):
        def get_value(match):
            env = openerp.http.request.env
            variable = match.group(1)
            value = env['test.variable'].search([('name', '=', variable)]).value
            return value or ''
        # regex pour remplacer les occurences de %variable_name% par leur valeur dans test_variable
        step = re.sub(r'%(\w+?)%', get_value, step)
        return super(WithVariablesParseMatcher, self).check_match(step)

matcher_mapping['with_variable'] = WithVariablesParseMatcher
use_step_matcher('with_variable')

class OdooResultSaver(Reporter):
    features = []

    def __init__(self, config):
        super(OdooResultSaver, self).__init__(config)
        self.lang_code = self.config.userdata['lang_code']
        self.target_id = self.config.userdata["target_id"]
        self.url = self.config.userdata['base_url']
        self.re = re.compile(".*@(\d+)@$")

    def feature(self, feature):
        self.features.append(feature)

    def end(self):
        for feature in self.features:
            self.register_feature(feature)
            
    def get_id(self, text):
        match = self.re.match(text)
        if match:
            return match.group(1)
        else:
            return None

    def register_feature(self, feature):
        env = openerp.http.request.env
        run_obj = env['run']
        if self.config.userdata['scenario_line_id']:
            return
        run_id = run_obj.create({
                                 'result':feature.status, 
                                 'lang_code':self.lang_code, 
                                 'target_id':self.target_id.id,
                                 'batch_id':self.config.userdata['batch_id'],
                                 'scenario_id':self.config.userdata['scenario_id'],})
        for scenario in feature.scenarios:
            self.register_scenario(scenario, run_id)
        self.config.userdata['run_id'] = run_id

    def register_scenario(self, scenario, run_id):
        env = openerp.http.request.env
        result_obj = env['scenario.result']
        scenario_id = env['scenario'].browse(int(self.get_id(scenario.name)))
        result_id = result_obj.create({
                                 'result':scenario.status, 
                                 'run_id':run_id.id,
                                 'scenario_id':scenario_id.id,
                                 'hide':scenario_id.hide,
                                 })
        for step in scenario.steps:
            self.register_step(step, result_id)

    def register_step(self, step, result_id):
        env = openerp.http.request.env
        result_line_obj = env['scenario.line.result']
        scenario_line_id = env['scenario.line'].browse(int(self.get_id(step.name)))
        data = {
                 'result':step.status, 
                 'scenario_result_id':result_id.id,
                 'scenario_line_id':scenario_line_id.id,
                 'error':step.error_message,
                 'hide':scenario_line_id.hide,
                 }
        if hasattr(step, 'screenshot_path') and step.screenshot_path is not None:
            screenshot_file = open(step.screenshot_path, 'rb')
            screenshot_data = screenshot_file.read().encode("base64")
            data['screenshot'] = screenshot_data
        if hasattr(step, 'label') and step.label is not None:
            data['label'] = step.label
        if hasattr(step, 'help_text') and step.help_text is not None:
            data['help_text'] = step.help_text
        result_line_obj.create(data)

try:
    webdriver.permanent_browser
except AttributeError:
    webdriver.permanent_browser = None
    print("reset browser")

def before_all(context):
    browser_vm_url = context.config.userdata['browser_vm_url']
    context.config.reporters.append(OdooResultSaver(context.config))
    if context.config.userdata['empty_batch']:
        if webdriver.permanent_browser is None:
            webdriver.permanent_browser = webdriver.Remote(
                                                 command_executor=browser_vm_url,
                                                 desired_capabilities=DesiredCapabilities.CHROME)
        else:
            try:
                webdriver.permanent_browser.get_window_position()
            except:
                webdriver.permanent_browser = webdriver.Remote(
                                                 command_executor=browser_vm_url,
                                                 desired_capabilities=DesiredCapabilities.CHROME)
        context.browser = webdriver.permanent_browser
            
    else:
        context.browser = webdriver.Remote(
                                           command_executor=browser_vm_url,
                                           desired_capabilities=DesiredCapabilities.CHROME)
    context.browser.maximize_window()
    context.wait = wait(context.browser, 20)

def after_all(context):
    if not context.config.userdata['empty_batch']:
        context.browser.quit()
    
def after_step(context, step):
    if step.status == 'failed':
        path = tempfile.NamedTemporaryFile().name
        context.browser.save_screenshot(path)
        context.screenshot = path
    if hasattr(context, 'screenshot') and context.screenshot is not None:
        step.screenshot_path = context.screenshot
        context.screenshot = None
    if hasattr(context, 'label') and context.label is not None:
        step.label = context.label
        context.label = None
    if hasattr(context, 'help_text') and context.help_text is not None:
        step.help_text = context.help_text
        context.help_text = None
