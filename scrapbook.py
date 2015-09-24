#just a scrapbook of code that might want to reference even if it's been taken out.


#raising errors
if templateName: errorMessage = str(self.keyName) + " not found in template " + templateName + "."
else: errorMessage = str(self.keyName) + " not found in template."
raise KeyError(errorMessage)