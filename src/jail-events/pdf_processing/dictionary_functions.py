import re

#function to proofread address

#function to parse Occurence Dictionary into Results

# needs function to break down the table into names, birthdates, incarceration dates, and charges - clean up stuff

# needs a function to assign an individual ID once names are cleaned up

clean_dict = {}

class DictionaryCleaner: 

    def __init__(self, scraped_dictionary):
        self.original_dictionary = scraped_dictionary
        self.clean_dict = {}

    def clean_facility_type(self):
        print ("tbd")

    def clean_name(self):
        name = self.original_dictionary["Facility Name"]
        pattern = r":\s*(.*?)\n"
        match = re.search(pattern, name)
        clean_name = match.group(1).strip()
        self.clean_dict["Facility Name"] = clean_name

    def clean_facility_address(self):
        print ("tbd")
    
    def clean_phone(self):
        phone = self.original_dictionary["Phone Number"]
        pattern = r":\s*(.*?)\n"
        match = re.search(pattern, phone)
        clean_phone = match.group(1).strip()
        self.clean_dict["Phone Number"] = clean_phone
    
    def clean_date(self):
        date = self.original_dictionary["Date"]
        pattern = r":\s*(.*?)\n"
        match = re.search(pattern, date)
        clean_date = match.group(1).strip()
        self.clean_dict["Date"] = clean_date
        #need to turn into numbers?

    def clean_time(self):
        clock_time = self.original_dictionary["Time of Day"]
        am_or_pm = self.original_dictionary["AM or PM"]
        #do time and AM/PM here
        print ("tbd")

    def clean_occurrence_dict(self):
        print ("tbd")

    def clean_table(self):
        print ("tbd")
    
    def clean_injuries(self):
        print ("tbd")

    def clean_resulting_death(self):
        print ("tbd")

    def clean_deceased_cause_date_time(self):
        if self.original_dictionary["Deceased Cause, Date, and Time"] == "N/A":
            pass
        #probably should split up

    def clean_suicide_watch(self):
        if self.original_dictionary["Deceased on Suicide Watch"] == "N/A":
            pass

    def clean_reported(self):
        if self.original_dictionary["Deceased Reporter"] == "N/A":
            pass

    def clean_deceased_examined(self):
        if self.original_dictionary["Deceased Examined by Physician"] == "N/A":
            pass
    
    def clean_deceased_illness(self):
        if self.original_dictionary["Deceased Signs of Illness"] == "N/A":
            pass


def main(scraped_dictionary):
    dictionary_cleaning = DictionaryCleaner(scraped_dictionary)
    dictionary_cleaning.clean_facility_type()
    dictionary_cleaning.clean_name()
    dictionary_cleaning.clean_phone()
    dictionary_cleaning.clean_date()
    dictionary_cleaning.clean_time()
    dictionary_cleaning.clean_occurrence_dict()
    dictionary_cleaning.clean_table()
    dictionary_cleaning.clean_injuries()

    #figure out smart way to do the optional stuff?

    return dictionary_cleaning.clean_dict

if __name__ == "__main__":
    main()
