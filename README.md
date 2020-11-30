<div align="center" markdown>
<img src="https://i.imgur.com/Wshzsv0.png"/>

# Add Properties To Image From CSV

<p align="center">
  <a href="#Overview">Overview</a> •
  <a href="#Preparation">Preparation</a> •
  <a href="#How-To-Run">How To Run</a>
</p>


[![](https://img.shields.io/badge/supervisely-ecosystem-brightgreen)]()
[![](https://img.shields.io/badge/slack-chat-green.svg?logo=slack)](https://supervise.ly/slack)
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/supervisely-ecosystem/add-properties-to-image-from-csv)
[![views](https://app.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/add-properties-to-image-from-csv&counter=views&label=views)](https://supervise.ly)
[![used by teams](https://app.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/add-properties-to-image-from-csv&counter=downloads&label=used%20by%20teams)](https://supervise.ly)
[![runs](https://app.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/add-properties-to-image-from-csv&counter=runs&label=runs&123)](https://supervise.ly)

</div>

## Overview

Application allows to add additional information to image from external databases. Developers add some identifiers to images during data aquisition quite often. But then additional human-readable information has to be assigned to images. Because ids are useless for labelers. 

Let's consider the example from retail industry. The same intuition can be applied to other industries as well: agriculture, self-driving cars, visul inspection and so on. Imaging that the task is to create reference images for every product in grocery store: label main object on every photo of grocery store shelves. But in many cases it is impossible to say what object is main: could you guess the main product on the picture from poster above just using `PRODUCT-ID:807090338`? 


But if we add information about product like category, item description, size, etc ... from our internal database (CSV file for simplicity), then labelers will be able to find the right main product on the image.

<img src="https://i.imgur.com/jtfh7mH.png"/>

To add properties to images it is needed to provide `CSV` file, name of image tag and name of csv column that will be used to match correct row from CSV with image. App takes given tag value from image, finds value in defined column and copies other columns of found CSV row to image. 


## Preparation

Prepare CSV file and upload it to team files. Here is the example of CSV file:

```csv
ITEM DESCRIPTION,CATEGORY,COMMERCIAL BRAND,SIZE,UPC CODE
Honey Nut Toasted Oats,cereal,PICS,12.3 oz,12217777
"Oats Cereal, Gluten Free",cereal,Honey Nut Cheerios,19.5 oz,807090338
"Frosted Flakes, Breakfast",cereal,Kellogg's,24 Oz,371107436
Frozen Blueberry Pancakes,waffles & pancakes,De Wafelbakkers,29.6 Oz,13399284
Buttermilk Waffles,waffles & pancakes,Great Value,29.6 oz,16382427
Chocolately Chip Waffles Easy Breakfast,waffles & pancakes,Kellogg's,29.6 oz,13399285
```

<img src="https://i.imgur.com/YtI2Htx.png"/>

Then copy path to the uploaded file:

<img src="https://i.imgur.com/ZcxrGgR.png"/>

# How To Run

**Step 1:** Add app to your team from Ecosystem if it is not there.

**Step 2:** Run app from the context menu of project

<img src="https://i.imgur.com/UHkbfRS.png" width="500px"/>

**Step 3:** Fill in the fields in modal window and press `Run` button

<img src="https://i.imgur.com/iaQV5Sw.png" width="600px"/>

**Step 4:** Wait until the task is finished, new project will be created, find link in task output

<img src="https://i.imgur.com/ziEkbmL.png"/>

**Step 5:** All warnings and errors can be found in task log

