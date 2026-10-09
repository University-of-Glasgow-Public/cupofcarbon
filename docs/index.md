# Cup of Carbon

Cup of Carbon estimates the dissolved organic carbon (DOC) concentration of
water samples from photographs taken with a smartphone. DOC is reported in
milligrams per litre (mg/L); darker water often has a higher DOC concentration.

This site contains:

- A [user guide](user-guide.md) for preparing and photographing samples.
- A [developer guide](developer-guide.md) for previewing and building this
  documentation.

## Features

- Site Registration: Users can register at Cup of Carbon to upload samples, create sites and view and delete their own uploads.

- Sample upload: This feature allows users to upload a top down image of peat water which will be sat on a printed out form, which is available for download. The form contains Aruco codes which allow the system to detect the paper and locate the cup containing the peat water within the paper

- Sample records: All valid samples are stored within the system and are viewable. Each record contains the DOC value and other meta data as well as a map of the location it was acquired and the image of the upload.

- Interactive maps: Upon loading of the home page users will be presented with an interactive map that will display all of the samples uploaded to Cup of Carbon. The samples are clickable and records can be accessed via this map.

- Sites: Registered users are able to add specific sites via an interactive map where they can create a polygon. This allows an samples uploaded to the application to be searched by their site if created.

- Sample search: Cup of Carbon has a search function which will return records based on search parameters 'Site', 'Date from' and 'Date to'. Search results are returned in the form of interactive map and as a paginated table.

- Sample download: The results of sample searches can be downloaded as a CSV. If the user wishes for a batch download they can leave all search parameters empty. Registered users can also download a copy of their own samples from their account page.

The method was developed and calibrated using 117 water samples photographed
with eight smartphone models. In testing, 95% of measurements were within
±12.3 mg/L of laboratory DOC values (Muir et al., 2025).
