1. Problem setting
Consider that you are a product developer developing and delivering a customized software product to a client. A product manager has given you some broad context, directions and requirements as below. You need to understand it, do additional learning and information gathering to gain sufficient knowledge of the domain, then develop the first version of the product based on it. You also need to:
- present and pitch the product to the client
- explain the software design and implementation to an internal technical lead reviewing the work

2. Requirement (from the product manager)
The client is an energy utility in the UK. They need to buy electricity from the wholesale market to serve their consumers. The specific team (that we are pitching the software to) is responsible for buying required power from the UK day-ahead market. More specifically, to meet their consumers' electricity demand, they need to understand how much power needs to be additionally procured (e.g., from thermal plants) beyond the generation available from renewable sources like wind. The power generation from renewable sources is weather-dependent, and the power purchase decisions from the day-ahead market need to be made one day before the delivery day. Hence, they need to rely on renewable generation forecasts when making decisions.

Using our web app product, they need to:
1. Clearly understand the latest renewable generation forecasts available when they need to make decisions on buying from the day-ahead market
2. Evaluate the accuracy of the renewable generation forecasts quantitatively, so that they can make their decisions considering the quantified error

To limit the scope of this challenge, for the above 2 purposes, we consider the national level generation of actuals and forecasts of wind power available from elexon alone (no other data beyond this).

2.1 Actual generation
The actual generation data for this is available at https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream. Please consider values corresponding to "fuelType" "WIND". Some relevant fields:
- "startTime": the target time (resolution of 30 minutes)
- "generation": generated wind power

2.2 Forecasted generation
The forecasts are available at https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream. Relevant fields:
- "startTime": similar to the "startTime" field in the actuals dataset
- "publishTime": the time at which the forecast was created
- "generation": similar to the "generation" field in the actuals dataset

Please consider data relevant only for purchase decisions to be made in January 2026.

Please build the application using React for front-end and Python for backend. You are free to use AI tools to assist with building this application (please mention it explicitly in the README if you've used AI tools). Please use docker. Please deploy the sample application in vercel or heroku.

Please do not spend more than 16 hours on this assignment. There is no deadline for submission. However, the earlier the better.

3. Deliverables
3.1 Video demo: unlisted YouTube video, max 10 minutes total. Part 1 (max 5 min): present the portal and analysis to the customer as the output of a pilot project, goal is to impress them. Part 2 (max 5 min): show the work to the tech lead for review; explain architecture, design, analysis, code base and key development practices; make review easy and provide clear knowledge transfer. Evaluation starts with the video.
3.2 Repo: public GitHub repo with an anonymous name. README must contain: details of the files and directories present, how to start the application, link to the vercel/heroku app.
3.3 Submit form: submit all details in the company's form; open each submitted URL in incognito mode to verify access.
