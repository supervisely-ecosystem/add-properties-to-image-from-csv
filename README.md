<div align="center" markdown>
<img src="https://i.imgur.com/Wshzsv0.png"/>

# Add Properties To Image From CSV

<p align="center">
  <a href="#Overview">Overview</a> •
  <a href="#How-To-Run">How To Run</a>
</p>

[![](https://img.shields.io/badge/slack-chat-green.svg?logo=slack)](https://supervise.ly/slack)
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/supervisely-ecosystem/add-properties-to-image-from-csv)
[![views](https://app.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/add-properties-to-image-from-csv&counter=views&label=views)](https://supervise.ly)
[![used by teams](https://app.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/add-properties-to-image-from-csv&counter=downloads&label=used%20by%20teams)](https://supervise.ly)
[![runs](https://app.supervise.ly/public/api/v3/ecosystem.counters?repo=supervisely-ecosystem/add-properties-to-image-from-csv&counter=runs&label=runs&123)](https://supervise.ly)

</div>

## Overview

Application allows to add additional information to image from external databases. Developers add some identifiers to images during data aquisition quite often. But then additional human-readable information has to be assigned to images. Because ids are useless for labelers. 

Let's consider the example from retail industry. The same intuition can be applied to many industries: agriculture, sel-driving cars, visul inspections and so on. Imaging that the task is to create reference images for every product in grocery store: label main object on every photo of grocery store shelves. But in many cases it is impossible to say what object is main: could you guess the main product on the picture from poster above just using `PRODUCT-ID:807090338`?


For example: in retail case it is a good idea to save product id (i.e. UPC code) of main object on the photos of grocery store shelves. This information might be really helpful during annotation process, because sometimes it is impossible to say, what main object has to be labeled (see banner). 

# add-properties-to-image-from-csv
Find row in CSV file and attach row data to image (as tags or as metadata)



during data aquisition -> labeling -> to help labelers

Examples: retail, agriculture, self-driving cars, medicine ...
