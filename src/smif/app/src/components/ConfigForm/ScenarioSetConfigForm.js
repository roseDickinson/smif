import React, { Component } from 'react'
import PropTypes from 'prop-types'
import update from 'immutability-helper'

import Popup from 'components/ConfigForm/General/Popup.js'
import PropertyList from 'components/ConfigForm/General/PropertyList.js'
import ScenarioConfigForm from 'components/ConfigForm/ScenarioSet/ScenarioConfigForm.js'
import FacetConfigForm from 'components/ConfigForm/ScenarioSet/FacetConfigForm.js'
import DeleteForm from 'components/ConfigForm/General/DeleteForm.js'
import { SaveButton, CancelButton } from 'components/ConfigForm/General/Buttons'

class ScenarioSetConfigForm extends Component {
    constructor(props) {
        super(props)

        this.handleChange = this.handleChange.bind(this)
        this.handleSave = this.handleSave.bind(this)
        this.handleFacetSave = this.handleFacetSave.bind(this)
        this.handleScenarioSave = this.handleScenarioSave.bind(this)
        this.handleScenarioCreate = this.handleScenarioCreate.bind(this)
        this.handleCancel = this.handleCancel.bind(this)

        this.openAddFacetPopup = this.openAddFacetPopup.bind(this)
        this.openEditFacetPopup = this.openEditFacetPopup.bind(this)
        this.closeFacetPopup = this.closeFacetPopup.bind(this)

        this.openAddScenarioPopup = this.openAddScenarioPopup.bind(this)
        this.openEditScenarioPopup = this.openEditScenarioPopup.bind(this)
        this.closeScenarioPopup = this.closeScenarioPopup.bind(this)

        this.openDeletePopup = this.openDeletePopup.bind(this)
        this.closeDeletePopup = this.closeDeletePopup.bind(this)
        this.deletePopupSubmit = this.deletePopupSubmit.bind(this)


        this.state = {
            scenarioSet: this.props.scenarioSet,
            selectedFacet: {},
            selectedScenario: {},
            selectedScenarios: this.props.scenarios.filter(scenario => scenario.scenario_set == this.props.scenarioSet.name),
            addFacetPopupIsOpen: false,
            editScenarioPopupIsOpen: false,
            deletePopupIsOpen: false
        }
    }

    handleChange(event) {
        const target = event.target
        const value = target.value
        const name = target.name

        if (name == 'Scenario') {
            this.setState({
                selectedScenarios: value
            })
        } else {
            this.setState({
                scenarioSet: update(this.state.scenarioSet, {[name]: {$set: value}})
            })
        }
    }

    handleSave() {
        // save the scenario set
        this.props.saveScenarioSet(this.state.scenarioSet)
    }

    handleFacetSave(facet) {
        const {facets} = this.props.scenarioSet

        if (facets.filter(curr_facet => curr_facet.name == facet.name).length > 0) {
            for (let i = 0; i < facets.length; i++) {
                if (facets[i].name == facet.name) facets[i] = facet
            }
        } else {
            facets.push(facet)
        }
        this.forceUpdate()
        this.closeFacetPopup()
    }

    handleFacetCreate(facet) {
        let {scenarioSet} = this.state
        scenarioSet.facets.push(facet)
        this.closeFacetPopup()
    }

    handleScenarioSave(saveScenario) {
        this.props.saveScenario(saveScenario)
        this.closeScenarioPopup()
    }

    handleScenarioCreate(scenario) {
        this.props.createScenario(scenario)
        this.closeScenarioPopup()
    }

    handleCancel() {
        this.props.cancelScenarioSet()
    }

    openAddFacetPopup() {
        this.setState({selectedFacet: {name: undefined, description: ''}})
        this.setState({addFacetPopupIsOpen: true})
    }

    closeFacetPopup() {
        this.setState({addFacetPopupIsOpen: false})
    }

    openEditFacetPopup(name) {
        const { scenarioSet} = this.props

        // Get id
        let id
        for (let i = 0; i < scenarioSet.facets.length; i++) {
            if (scenarioSet.facets[i].name == name) {
                id = i
            }
        }

        this.setState({selectedFacet: Object.assign({}, scenarioSet.facets[id])})
        this.setState({addFacetPopupIsOpen: true})
    }

    openAddScenarioPopup() {
        const { scenarioSet} = this.props

        // prepare facets
        let new_facets = []

        for (let set_facet of scenarioSet.facets) {
            new_facets.push({
                'name': set_facet.name,
                'filename': '',
                'spatial_resolution': '',
                'temporal_resolution': '',
                'units': ''
            })
        }

        this.setState({selectedScenario: { name: undefined, description: '', 'facets': new_facets, 'scenario_set': scenarioSet['name'] }})
        this.setState({editScenarioPopupIsOpen: true})
    }

    closeScenarioPopup() {
        this.setState({editScenarioPopupIsOpen: false})
    }

    openEditScenarioPopup(name) {

        const { scenarioSet, scenarios} = this.props

        // Get id
        let id
        for (let i = 0; i < scenarios.length; i++) {
            if (scenarios[i].name == name) {
                id = i
            }
        }

        // update facets
        let new_facets = []

        for (let set_facet of scenarioSet.facets) {
            if(scenarios[id].facets.filter(scenario_facet => scenario_facet.name == set_facet.name).length) {
                // copy existing settings
                for (let i = 0; i < scenarios[id].facets.length; i++) {
                    if (scenarios[id].facets[i].name == set_facet.name) new_facets.push(scenarios[id].facets[i])
                }
            } else {
                new_facets.push({
                    'name': set_facet.name,
                    'filename': '',
                    'spatial_resolution': '',
                    'temporal_resolution': '',
                    'units': ''
                })
            }
        }
        scenarios[id].facets = new_facets

        // load scenario
        this.setState({selectedScenario: Object.assign({}, scenarios[id])})
        this.setState({editScenarioPopupIsOpen: true})
    }

    openDeletePopup(event) {

        let target_in_use_by = []

        switch(event.target.name) {
        case 'Facet':
            this.props.sosModels.forEach(function(sos_model) {
                sos_model.dependencies.forEach(function(dependency) {
                    if (event.target.value == dependency.source_model_output) {
                        target_in_use_by.push({
                            name: sos_model.name,
                            link: '/configure/sos-models/',
                            type: 'SosModel'
                        })
                    }
                })
            })
            break

        case 'Scenario':
            this.props.sosModelRuns.forEach(function(sos_model_run) {
                Object.keys(sos_model_run.scenarios).forEach(function(key) {
                    if (event.target.value == sos_model_run.scenarios[key]) {
                        target_in_use_by.push({
                            name: sos_model_run.name,
                            link: '/configure/sos-model-run/',
                            type: 'SosModelRun'
                        })
                    }
                })
            })
            break
        }

        this.setState({
            deletePopupIsOpen: true,
            deletePopupConfigName: event.target.value,
            deletePopupType: event.target.name,
            deletePopupInUseBy: target_in_use_by
        })
    }

    deletePopupSubmit() {

        const {deletePopupType, deletePopupConfigName } = this.state
        const {scenarioSet} = this.props

        switch(deletePopupType) {
        case 'facets':
            for (let i = 0; i < Object.keys(scenarioSet.facets).length; i++) {
                if (scenarioSet.facets[i].name == deletePopupConfigName) {
                    scenarioSet.facets.splice(i, 1)
                }
            }
            break

        case 'scenarios':
            this.props.deleteScenario(deletePopupConfigName)
            break
        }

        this.closeDeletePopup(deletePopupType)
        this.forceUpdate()
    }

    closeDeletePopup() {
        this.setState({deletePopupIsOpen: false})
    }

    renderScenarioSetConfigForm(scenarioSet, selectedScenarios, selectedScenario, selectedFacet) {

        // Do not show scenarios when there are no facets configured
        let scenarioCardState = 'collapse show'
        if (scenarioSet.facets.length == 0) {
            scenarioCardState = 'collapse'
        }

        // Check if facets are configured in all scenario sets
        // prepare an array with warning
        let scenarioWarnings = []

        let facetlist = []
        for (let facet of scenarioSet.facets) {
            facetlist.push(facet['name'])
        }
        for (let scenario in selectedScenarios) {
            let scenarioFacetList = []
            for (let facet of selectedScenarios[scenario]['facets']) {
                scenarioFacetList.push(facet['name'])
            }

            if (facetlist.toString() == scenarioFacetList.toString()) {
                scenarioWarnings.push(false)
            } else {
                scenarioWarnings.push(true)
            }
        }

        return (
            <div>
                <div className="card">
                    <div className="card-header">General</div>
                    <div className="card-body">

                        <div className="form-group row">
                            <label className="col-sm-2 col-form-label">Name</label>
                            <div className="col-sm-10">
                                <input id="scenario_set_name" className="form-control" name="name" type="text" disabled="true" defaultValue={scenarioSet.name} onChange={this.handleChange}/>
                            </div>
                        </div>

                        <div className="form-group row">
                            <label className="col-sm-2 col-form-label">Description</label>
                            <div className="col-sm-10">
                                <textarea id="scenario_set_description" className="form-control" name="description" rows="5" defaultValue={scenarioSet.description} onChange={this.handleChange}/>
                            </div>
                        </div>

                    </div>
                </div>

                <div className="card">
                    <div className="card-header">Facets</div>
                    <div className="card-body">
                        <PropertyList itemsName="facets" items={scenarioSet.facets} columns={{name: 'Name', description: 'Description'}} editButton={true} deleteButton={true} onEdit={this.openEditFacetPopup} onDelete={this.openDeletePopup} />
                        <input id='btn_add_facet' className="btn btn-secondary btn-lg btn-block btn-margin" name="createFacet" type="button" value="Add Facet" onClick={this.openAddFacetPopup}/>
                    </div>
                </div>

                <div className={scenarioCardState} >
                    <div className="card">
                        <div className="card-header">Scenarios</div>
                        <div className="card-body">
                            <PropertyList itemsName="scenarios" items={selectedScenarios} columns={{name: 'Name', description: 'Description'}} enableWarnings={true} rowWarning={scenarioWarnings} editButton={true} deleteButton={true} onEdit={this.openEditScenarioPopup} onDelete={this.openDeletePopup} />
                            <input id="btn_createScenario" className="btn btn-secondary btn-lg btn-block btn-margin" name="createScenario" type="button" value="Add Scenario" onClick={this.openAddScenarioPopup}/>
                        </div>
                    </div>
                </div>

                <SaveButton id="btn_saveScenarioSet" onClick={this.handleSave} />
                <CancelButton id="btn_cancelScenarioSet" onClick={this.handleCancel} />

                <Popup name='popup_delete' onRequestOpen={this.state.deletePopupIsOpen}>
                    <DeleteForm config_name={this.state.deletePopupConfigName} config_type={this.state.deletePopupType} in_use_by={this.state.deletePopupInUseBy} submit={this.deletePopupSubmit} cancel={this.closeDeletePopup}/>
                </Popup>

                <Popup name='popup_add_facet' onRequestOpen={this.state.addFacetPopupIsOpen}>
                    <form onSubmit={(e) => {e.preventDefault(); e.stopPropagation()}}>
                        <FacetConfigForm facet={selectedFacet} saveFacet={this.handleFacetSave} cancelFacet={this.closeFacetPopup}/>
                    </form>
                </Popup>

                <Popup name='popup_scenario_config_form' onRequestOpen={this.state.editScenarioPopupIsOpen}>
                    <form onSubmit={(e) => {e.preselectedScenarioventDefault(); e.stopPropagation()}}>
                        <ScenarioConfigForm scenario={selectedScenario} scenarioSet={scenarioSet} createScenario={this.handleScenarioCreate} saveScenario={this.handleScenarioSave} cancelScenario={this.closeScenarioPopup}/>
                    </form>
                </Popup>
            </div>
        )
    }

    renderDanger(message) {
        return (
            <div>
                <div id="alert-danger" className="alert alert-danger">
                    {message}
                </div>
                <CancelButton onClick={this.handleCancel} />
            </div>
        )
    }

    render() {
        const {scenarioSet, selectedScenario, selectedFacet} = this.state
        

        let selectedScenarios = this.props.scenarios.filter(scenario => scenario.scenario_set == this.props.scenarioSet.name)

        // Auto-fixable problems with configuration
        if (scenarioSet.facets == null || scenarioSet.facets == undefined) {
            // The scenarioSet does not have a scenarioSet.facets array
            // this will crash the code, and is therefore fixed by this line
            scenarioSet.facets = []
        }

        if (scenarioSet.name == undefined) {
            return this.renderDanger('This Scenario Set does not exist.')
        } else {
            return this.renderScenarioSetConfigForm(scenarioSet, selectedScenarios, selectedScenario, selectedFacet)
        }
    }
}

ScenarioSetConfigForm.propTypes = {
    sosModelRuns: PropTypes.array.isRequired,
    sosModels: PropTypes.array.isRequired,
    scenarioSet: PropTypes.object.isRequired,
    scenarios: PropTypes.array.isRequired,
    saveScenarioSet: PropTypes.func,
    createScenario: PropTypes.func,
    saveScenario: PropTypes.func,
    deleteScenario: PropTypes.func,
    cancelScenarioSet: PropTypes.func
}

ScenarioSetConfigForm.defaultProps = {
    sosModelRuns: [],
    sosModels: [],
    scenarioSet: {},
    scenarios: []
}

export default ScenarioSetConfigForm
