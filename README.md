# Cup of Carbon

Cup of Carbon is a web application that allows users to engage in citizen science. That is any citizen can participate in assisting with the research. Users can upload a top down image of a cup of peat water and the system will perform a calculation to assess the dissolved organic carbon (DOC). Users may browse their own samples if registered and can navigate the application to view samples which others have uploaded.

# Features

- Site Registration: Users can register at Cup of Carbon to upload samples, create sites and view and delete their own uploads.

- Sample upload: This feature allows users to upload a top down image of peat water which will be sat on a printed out form, which is available for download. The form contains Aruco codes which allow the system to detect the paper and locate the cup containing the peat water within the paper

- Sample records: All valid samples are stored within the system and are viewable. Each record contains the DOC value and other meta data as well as a map of the location it was acquired and the image of the upload.

- Interactive maps: Upon loading of the home page users will be presented with an interactive map that will display all of the samples uploaded to Cup of Carbon. The samples are clickable and records can be accessed via this map.

- Sites: Registered users are able to add specific sites via an interactive map where they can create a polygon. This allows an samples uploaded to the application to be searched by their site if created.

- Sample search: Cup of Carbon has a search function which will return records based on search parameters 'Site', 'Date from' and 'Date to'. Search results are returned in the form of interactive map and as a paginated table.

- Sample download: The results of sample searches can be downloaded as a CSV. If the user wishes for a batch download they can leave all search parameters empty. Registered users can also download a copy of their own samples from their account page.

## Technology Stack 

	### Backend 
	- Flask 
	- PyMongo 
	- OpenCV 
	- NumPy 

	### Frontend 
	- Jinja2 
	- JavaScript 
	- Bootstrap 
	- Leaflet 

	### Database 
	- MongoDB 

	### Infrastructure 
	- Azure VM

## Architecture

The application follows a server-rendered architecture using Flask and Jinja2.

1. Flask handles routing, authentication, business logic, and database access.
2. Jinja2 templates render dynamic HTML pages on the server.
3. JavaScript provides client-side interactivity where required.
4. MongoDB stores application data.

Browser
    |
    v
Flask Routes
    |
    +--> Business Logic
    |
    +--> MongoDB
    |
    +--> Jinja2 Templates
            |
            v
        HTML Response


## Prerequisites

- Python 3.12+
- MongoDB
- Git
- Docker (optional)

## Installation

Clone the repository:

git clone https://github.com/uog-rcaas/Colorimetry.git
cd cup-of-carbon

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
