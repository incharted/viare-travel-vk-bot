from vkbottle import BaseStateGroup


class TourSelectionState(BaseStateGroup):
    SCOPE = "scope"
    DESTINATION = "destination"
    BUDGET = "budget"
    DATES = "dates"
    TRAVELERS = "travelers"
    REST_TYPE = "rest_type"
    CONFIRMATION = "confirmation"


class AdminState(BaseStateGroup):
    BROADCAST = "broadcast"
    REPLY_VK = "reply_vk"
    REPLY_REQUEST = "reply_request"
    REQUEST_CARD = "request_card"
    REQUEST_CLOSE = "request_close"
    CONTENT_EDIT = "content_edit"
    TOUR_ADD_NAME = "tour_add_name"
    TOUR_ADD_COUNTRY = "tour_add_country"
    TOUR_ADD_PRICE = "tour_add_price"
    TOUR_ADD_DAYS = "tour_add_days"
    TOUR_ADD_REST = "tour_add_rest"
    TOUR_ADD_DATES = "tour_add_dates"
    TOUR_ADD_DESCRIPTION = "tour_add_description"
    TOUR_ADD_PHOTO = "tour_add_photo"
    TOUR_DISABLE = "tour_disable"
    TOUR_ENABLE = "tour_enable"
    TOUR_PRICE = "tour_price"
