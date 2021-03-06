import * as actionTypes from './actionTypes';
import { queryAwards } from '../../../services/api';


const changePage = (payload) => ({
  type: actionTypes.CHANGE_PAGE,
  data: payload.awards,
  currentPage: payload.page,
  count: payload.counts
})

export const changePageData = (page, cb) => {
  return async (dispatch) => {
    const result = await queryAwards({page: page})
    const action = changePage(Object.assign(result, {page: page}))
    dispatch(action)
    if ( cb ) cb()
  }
}

export const setAwardList = (newAwardList) => ({
  type: actionTypes.SET_AWARD_LIST,
  newAwardList: newAwardList
})
